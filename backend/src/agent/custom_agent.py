import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Type

from browser_use.agent.prompts import AgentMessagePrompt, SystemPrompt
from browser_use.agent.service import Agent
from browser_use.agent.views import (
    ActionModel,
    ActionResult,
    AgentHistory,
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.browser.views import BrowserState, BrowserStateHistory
from browser_use.controller.service import Controller
from browser_use.telemetry.views import AgentEndTelemetryEvent, AgentStepTelemetryEvent
from browser_use.utils import time_execution_async
from json_repair import repair_json
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from src.terminal.Terminal_message_manager import TerminalMessageManager
from src.utils.agent_state import AgentState

from .custom_massage_manager import CustomMassageManager
from .custom_views import CustomAgentOutput, CustomAgentStepInfo

logger = logging.getLogger(__name__)


class CustomAgent(Agent):
    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        add_infos: str = "",
        browser: Browser | None = None,
        browser_context: BrowserContext | None = None,
        controller: Controller = Controller(),
        use_vision: bool = True,
        max_failures: int = 5,
        retry_delay: int = 10,
        system_prompt_class: Type[SystemPrompt] = SystemPrompt,
        agent_prompt_class: Type[AgentMessagePrompt] = AgentMessagePrompt,
        max_input_tokens: int = 128000,
        validate_output: bool = False,
        include_attributes: list[str] = [
            "title",
            "type",
            "name",
            "role",
            "tabindex",
            "aria-label",
            "placeholder",
            "value",
            "alt",
            "aria-expanded",
        ],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,
        tool_call_in_content: bool = True,
        agent_state: AgentState = None,  # type: ignore
        initial_actions: Optional[List[Dict[str, Dict[str, Any]]]] = None,
        # Cloud Callbacks
        register_new_step_callback: (
            Callable[["BrowserState", "AgentOutput", int], None] | None  # type: ignore
        ) = None,  # type: ignore
        register_done_callback: Callable[["AgentHistoryList"], None] | None = None,
        tool_calling_method: Optional[str] = "auto",
        limit_num_image_per_llm_call=None,
    ):
        super().__init__(
            task=task,
            llm=llm,
            browser=browser,
            browser_context=browser_context,
            controller=controller,
            use_vision=use_vision,
            max_failures=max_failures,
            retry_delay=retry_delay,
            system_prompt_class=system_prompt_class,
            max_input_tokens=max_input_tokens,
            validate_output=validate_output,
            include_attributes=include_attributes,
            max_error_length=max_error_length,
            max_actions_per_step=max_actions_per_step,
            tool_call_in_content=tool_call_in_content,
            initial_actions=initial_actions,
            register_new_step_callback=register_new_step_callback,
            register_done_callback=register_done_callback,
            tool_calling_method=tool_calling_method,
        )

        # record last actions
        self._last_actions = None
        # custom new info
        self.add_infos = add_infos
        # agent_state for Stop
        self.agent_state = agent_state
        self.agent_prompt_class = agent_prompt_class
        self.message_manager = CustomMassageManager(
            llm=self.llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=self.system_prompt_class,
            agent_prompt_class=agent_prompt_class,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
        )
        self.limit_num_image_per_llm_call = limit_num_image_per_llm_call
        self.terminal_message_manager = TerminalMessageManager()

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        # Get the dynamic action model from controller's registry
        self.ActionModel = self.controller.registry.create_action_model()
        # Create output model with the dynamic actions
        self.AgentOutput = CustomAgentOutput.type_with_custom_actions(self.ActionModel)

    def _log_response(self, response: CustomAgentOutput) -> None:
        """Log the model's response"""
        if "Success" in response.current_state.prev_action_evaluation:
            emoji = "✅"
        elif "Failed" in response.current_state.prev_action_evaluation:
            emoji = "❌"
        else:
            emoji = "🤷"

        logger.info(f"{emoji} Eval: {response.current_state.prev_action_evaluation}")
        logger.info(f"🧠 New Memory: {response.current_state.important_contents}")
        logger.info(f"⏳ Task Progress: \n{response.current_state.task_progress}")
        logger.info(f"📋 Future Plans: \n{response.current_state.future_plans}")
        logger.info(f"🤔 Thought: {response.current_state.thought}")
        logger.info(f"🎯 Summary: {response.current_state.summary}")
        for i, action in enumerate(response.action):
            logger.info(
                f"🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}"
            )

    def update_step_info(
        self, model_output: CustomAgentOutput, step_info: CustomAgentStepInfo = None  # type: ignore
    ):
        """
        update step info
        """
        if step_info is None:
            return

        step_info.step_number += 1
        important_contents = model_output.current_state.important_contents
        if (
            important_contents
            and "None" not in important_contents
            and important_contents not in step_info.memory
        ):
            step_info.memory += important_contents + "\n"

        task_progress = model_output.current_state.task_progress
        if task_progress and "None" not in task_progress:
            step_info.task_progress = task_progress

        future_plans = model_output.current_state.future_plans
        if future_plans and "None" not in future_plans:
            step_info.future_plans = future_plans

    @time_execution_async("--get_next_action")
    async def get_next_action(
        self,
        input_messages: list[BaseMessage],
    ) -> AgentOutput:
        """Get next action from LLM based on current state"""
        messages_to_process = input_messages

        if self.limit_num_image_per_llm_call is not None:
            NUM_IMAGES_TO_KEEP = self.limit_num_image_per_llm_call
            images_found = 0

            # Iterate over images in reverse
            for msg in reversed(messages_to_process):
                content = msg.content
                # The content can be either a string, or a list of dicts or strings
                if isinstance(content, list):
                    # Iterate over content in reverse
                    for i in range(len(content) - 1, -1, -1):
                        item = content[i]
                        # if it's got an image
                        if isinstance(item, dict) and "image_url" in item:
                            # and we haven't reached the limit
                            if images_found <= NUM_IMAGES_TO_KEEP:
                                # keep the image and increment the count
                                images_found += 1
                            else:
                                # otherwise remove the image from the content
                                del content[i]

        # Call the LLM with the messages
        ai_message = self.llm.invoke(messages_to_process)
        self.message_manager._add_message_with_tokens(ai_message)

        if isinstance(ai_message.content, list):
            ai_content = ai_message.content[0]
        else:
            ai_content = ai_message.content

        ai_content = ai_content.replace("```json", "").replace(
            "```", ""
        )  # type: ignore
        ai_content = repair_json(ai_content)

        logger.info("Raw Model Responses:")
        logger.info(ai_content)

        try:
            parsed_json = json.loads(ai_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Problematic content: {ai_content}")
            raise

        parsed_json = json.loads(ai_content)  # type: ignore

        if not isinstance(parsed_json, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
        # Add default current_state if missing
        if "current_state" not in parsed_json:
            parsed_json["current_state"] = {}

        current_state = parsed_json["current_state"]
        default_fields = {
            "prev_action_evaluation": "",
            "important_contents": "",
            "task_progress": "",
            "future_plans": "",
            "thought": "Initial analysis",
            "summary": "Starting task execution",
        }

        for field, default_value in default_fields.items():
            if field not in current_state:
                current_state[field] = default_value

        logger.info("Structured response before parsing:")
        logger.info(json.dumps(parsed_json, indent=2))

        try:
            parsed: AgentOutput = self.AgentOutput(**parsed_json)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise

        if parsed is None:
            logger.debug(ai_message.content)
            raise ValueError("Could not parse response.")

        # Limit actions to maximum allowed per step
        parsed.action = parsed.action[: self.max_actions_per_step]
        self._log_response(parsed)
        self.n_steps += 1

        return parsed

    async def step(self, step_info: Optional[CustomAgentStepInfo] = None) -> AsyncIterator[AgentHistory]:
       """Execute one step of the task with streaming"""
       logger.info(f"\n📍 Step {self.n_steps}")
    
       state = None
       model_output = None
       result: list[ActionResult] = []
    
       try:
           # Get browser state
           if self.browser_context:
               state = await self.browser_context.get_state(use_vision=self.use_vision)
            
           self.message_manager.add_state_message(
               state, self._last_actions, self._last_result, step_info,
               terminal_message_manager=self.terminal_message_manager if hasattr(self, "terminal_message_manager") else None
           )
        
           # Get terminal state if available
           terminal_state = self.terminal_message_manager.get_last_state() if hasattr(self, "terminal_message_manager") else None
        
           input_messages = self.message_manager.get_messages()
        
           try:
               # Get model output
               model_output = await self.get_next_action(input_messages)
            
               if model_output is None:
                   logger.error("Model output is None")
                   return
                
               # Check If there are terminal actions
               actions: list[ActionModel] = model_output.action
               has_terminal_actions = any("execute_terminal_command" in action.model_dump_json(exclude_unset=True) for action in actions)
            
               if hasattr(self, "register_new_step_callback") and self.register_new_step_callback:
                   if has_terminal_actions and terminal_state:
                       # Create a BrowserStateHistory for terminal state
                       compatible_state = self._create_terminal_compatible_browser_state(terminal_state)
                       self.register_new_step_callback(compatible_state, model_output, self.n_steps)
                   else:
                       self.register_new_step_callback(state, model_output, self.n_steps)
                    
               self.update_step_info(model_output, step_info)
            
               #Create state for history item
               if has_terminal_actions and terminal_state:
                   state_for_history = self._create_terminal_compatible_browser_state(terminal_state)
               else:
                   state_for_history = state
                
               # Stream output immediately
               self._make_history_item(model_output, state_for_history, result)
               yield self.history.history[-1]
            
           except Exception as e:
               logger.error(f"Error generating thought: {e}")
               self._make_history_item(
                   None, state, [ActionResult(error=str(e), is_done=False)]
               )
               yield self.history.history[-1]
               return
            
           # Execute actions
           if has_terminal_actions:
               result: list[ActionResult] = await self.controller.multi_act(actions, None) 
               if result and result[0].error:
                   logger.error(f"Error executing terminal action: {result[0].error}")
                
                   if terminal_state:
                       state_for_history = self._create_terminal_compatible_browser_state(terminal_state)
                   else:
                       state_for_history = self._create_empty_state()
               elif result and hasattr(self, "terminal_message_manager"):
                   terminal_output = result[0].extracted_content if result[0].extracted_content else ""
                   working_directory = ""
                
                   if "Directory:" in terminal_output:
                       try:
                           working_directory = terminal_output.split("Directory:", 1)[-1].split("\n")[0].strip()
                       except:
                           working_directory = terminal_state['working_directory'] if terminal_state else ""
                
                   # Update terminal state
                   self.terminal_message_manager.add_state_message(
                       terminal_id=terminal_state['terminal_id'] if terminal_state else "",
                       output=terminal_output,
                       working_directory=working_directory,
                       step_info=step_info
                   )
                
                   updated_terminal_state = self.terminal_message_manager.get_last_state()
                   state_for_history = self._create_terminal_compatible_browser_state(updated_terminal_state)
                
                   # Update the message manager with the terminal results so future model outputs will see the terminal results
                   self.message_manager.add_state_message(
                       state_for_history,
                       None,
                       result,
                       step_info,
                       terminal_message_manager=self.terminal_message_manager
                   )
               else:
                   state_for_history = self._create_empty_state()
           else:
               result: list[ActionResult] = await self.controller.multi_act(actions, self.browser_context)
               state_for_history = state
        
           # Handle partial actions
           if len(result) != len(actions):
               for ri in range(len(result), len(actions)):
                   result.append(
                       ActionResult(
                           extracted_content=None,
                           include_in_memory=True,
                           error=f"{actions[ri].model_dump_json(exclude_unset=True)} is Failed to execute.",
                           is_done=False,
                       )
                   )
                
           # Update last actions and results (only for browser actions)
           if not has_terminal_actions:
               self._last_actions = actions
               self._last_result = result
            
           # Make a new history item with the action results
           self._make_history_item(None, state_for_history, result)
           yield self.history.history[-1]
        
       except Exception as e:
           result = await self._handle_step_error(e)
           self._make_history_item(None, state, result)
           yield self.history.history[-1]
       finally:
           # Telemetry Capture
           actions_data = (
               [a.model_dump(exclude_unset=True) for a in model_output.action]
               if model_output
               else []
           )
        
           self.telemetry.capture(
               AgentStepTelemetryEvent(
                   agent_id=self.agent_id,
                   step=self.n_steps,
                   actions=actions_data,
                   consecutive_failures=self.consecutive_failures,
                   step_error=(
                       [r.error for r in result if r.error]
                       if result
                       else ["No result"]
                   ),
               )
           )
           
    async def run(self, max_steps: int = 100) -> AsyncIterator[AgentHistory]:
        """Execute the task with maximum number of steps"""
        try:
            self._log_agent_run()

            # Execute initial actions if provided
            if self.initial_actions:
                result = await self.controller.multi_act(
                    self.initial_actions,
                    self.browser_context,
                    check_for_new_elements=False,
                )
                self._last_result = result

            step_info = CustomAgentStepInfo(
                task=self.task,
                add_infos=self.add_infos,
                step_number=1,
                max_steps=max_steps,
                memory="",
                task_progress="",
                future_plans="",
            )

            for step in range(max_steps):
                # 1) Check if stop requested
                if self.agent_state and self.agent_state.is_stop_requested():
                    logger.info("🛑 Stop requested by user")
                    self._create_stop_history_item()
                    break

                # 2) Store last valid state before step
                if self.browser_context and self.agent_state:
                    state = await self.browser_context.get_state(
                        use_vision=self.use_vision
                    )
                    self.agent_state.set_last_valid_state(state)

                if self._too_many_failures():
                    break
                async for history_item in self.step(step_info):
                    yield history_item

                # # 3) Do the step
                # await self.step(step_info)

                if self.history.is_done():
                    if (
                        self.validate_output and step < max_steps - 1
                    ):  # if last step, we dont need to validate
                        if not await self._validate_output():
                            continue

                    logger.info("✅ Task completed successfully")
                    break
            else:
                logger.info("❌ Failed to complete task in maximum steps")

            # return self.history

        finally:
            self.telemetry.capture(
                AgentEndTelemetryEvent(
                    agent_id=self.agent_id,
                    success=self.history.is_done(),
                    steps=self.n_steps,
                    max_steps_reached=self.n_steps >= max_steps,
                    errors=self.history.errors(),
                )
            )

            if not self.injected_browser_context:
                await self.browser_context.close()

            if not self.injected_browser and self.browser:
                await self.browser.close()

            yield AgentHistory(
                model_output=None,
                state=self._create_empty_state(),
                result=[ActionResult(extracted_content=None, error=None, is_done=True)],
            )

    def _create_stop_history_item(self):
        """Create a history item for when the agent is stopped."""
        try:
            # Attempt to retrieve the last valid state from agent_state
            state = None
            if self.agent_state:
                last_state = self.agent_state.get_last_valid_state()
                if last_state:
                    # Convert to BrowserStateHistory
                    state = BrowserStateHistory(
                        url=getattr(last_state, "url", ""),
                        title=getattr(last_state, "title", ""),
                        tabs=getattr(last_state, "tabs", []),
                        interacted_element=[None],
                        screenshot=getattr(last_state, "screenshot", None),
                    )
                else:
                    state = self._create_empty_state()
            else:
                state = self._create_empty_state()

            # Create a final item in the agent history indicating done
            stop_history = AgentHistory(
                model_output=None,
                state=state,
                result=[ActionResult(extracted_content=None, error=None, is_done=True)],
            )
            self.history.history.append(stop_history)

        except Exception as e:
            logger.error(f"Error creating stop history item: {e}")
            # Create empty state as fallback
            state = self._create_empty_state()
            stop_history = AgentHistory(
                model_output=None,
                state=state,
                result=[ActionResult(extracted_content=None, error=None, is_done=True)],
            )
            self.history.history.append(stop_history)

    def _convert_to_browser_state_history(self, browser_state):
        return BrowserStateHistory(
            url=getattr(browser_state, "url", ""),
            title=getattr(browser_state, "title", ""),
            tabs=getattr(browser_state, "tabs", []),
            interacted_element=[None],
            screenshot=getattr(browser_state, "screenshot", None),
        )

    def _create_empty_state(self):
        return BrowserStateHistory(
            url="", title="", tabs=[], interacted_element=[None], screenshot=None
        )
    def _create_terminal_compatible_browser_state(self, terminal_state):
        """Create a BrowserStateHistory compatible object from terminal state."""
        terminal_id = terminal_state.get("terminal_id", "")
        working_directory = terminal_state.get("working_directory", "")

        return BrowserStateHistory(
            url=f"terminal://{terminal_id}",
            title=f"Terminal - {working_directory}",
            tabs=[],
            interacted_element=[None],
            screenshot=None,
        )

    def _make_history_item(
       self,
       model_output: AgentOutput | None,
       state: BrowserState,
       result: list[ActionResult],
    ) -> None:
       """Create and store history item with special handling for terminal states"""

       if state is None:
           state_history = BrowserStateHistory(
               url="",
               title="",
               tabs=[],
               interacted_element=[None],
               screenshot=None,
           )

           history_item = AgentHistory(model_output=model_output, result=result, state=state_history)
           self.history.history.append(history_item)
           return
    
       # Check if this is a terminal state
       is_terminal_state = (
           hasattr(state, 'url') and 
           state.url and 
           state.url.startswith("terminal://")
       )
    
       # Fix selector_map access error
       if is_terminal_state:
           # Create a BrowserStateHistory without trying to access selector_map
           state_history = BrowserStateHistory(
               url=state.url,
               title=state.title,
               tabs=state.tabs if hasattr(state, 'tabs') else [],
               interacted_element=[None],  
               screenshot=state.screenshot if hasattr(state, 'screenshot') else None,
           )

        
        
           history_item = AgentHistory(model_output=model_output, result=result, state=state_history)
           self.history.history.append(history_item)
           return
    
       # Regular browser state - create history item normally
       interacted_elements = None
    
       if model_output:
           # Handle potential selector_map absence
           if hasattr(state, 'selector_map'):
               interacted_elements = AgentHistory.get_interacted_element(model_output, state.selector_map)
           else:
               interacted_elements = [None] * len(model_output.action)
       else:
           interacted_elements = [None]
    
       state_history = BrowserStateHistory(
           url=state.url,
           title=state.title,
           tabs=state.tabs,
           interacted_element=interacted_elements,
           screenshot=state.screenshot,
       )
    
       history_item = AgentHistory(model_output=model_output, result=result, state=state_history)
       self.history.history.append(history_item)