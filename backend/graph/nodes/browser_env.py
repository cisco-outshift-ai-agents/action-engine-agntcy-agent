import json
import logging
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from browser_use.agent.views import ActionModel, ActionResult
from browser_use.controller.service import Controller
from core.types import AgentState, EnvironmentType
from environments.browser.prompts import get_browser_prompt
from environments.browser.schemas import BrowserResponse
from src.agent.custom_prompts import CustomAgentMessagePrompt
from src.agent.custom_views import CustomAgentStepInfo

logger = logging.getLogger(__name__)


def _convert_tabs_to_dict(tabs):
    """Convert TabInfo objects to dictionaries"""
    if not tabs:
        return []
    return [
        {"page_id": tab.page_id, "url": tab.url, "title": tab.title} for tab in tabs
    ]


class BrowserEnvNode:
    """Handles browser environment execution with agent-like behavior"""

    def __init__(self):
        self.name = "browser_env"
        self.controller = Controller()
        self.max_retries = 3
        self.consecutive_failures = 0
        self.step_number = 0
        self.max_steps = 100  # Default value, could be made configurable

    async def __call__(self, state: AgentState, config: Dict):
        return await self.ainvoke(state, config)

    async def ainvoke(self, state: AgentState, config: Dict) -> Dict:
        logger.info("BrowserEnvNode: Starting execution")
        llm = config.get("configurable", {}).get("llm")
        env_registry = config.get("configurable", {}).get("env_registry", {})
        browser_env = env_registry.get(EnvironmentType.BROWSER)

        if not browser_env or not llm:
            logger.error("BrowserEnvNode: Missing required components")
            return Command(goto="end")

        try:
            browser_state = await browser_env.browser_context.get_state(use_vision=True)
            state_dict = {
                "url": getattr(browser_state, "url", ""),
                "title": getattr(browser_state, "title", ""),
                "elements": getattr(browser_state, "elements", []),
                "tabs": _convert_tabs_to_dict(getattr(browser_state, "tabs", [])),
            }

            logger.debug(f"Current browser state: {json.dumps(state_dict, indent=2)}")

            # Create prompt
            prompt = get_browser_prompt(
                task=state["task"],
                elements=state_dict["elements"],
                current_url=state_dict["url"],
                tabs=state_dict["tabs"],
            )

            # Create the detailed state message using CustomAgentMessagePrompt
            self.step_number += 1
            step_info = CustomAgentStepInfo(
                task=state["task"],
                add_infos="",  # Could be added to state if needed
                step_number=self.step_number,
                max_steps=self.max_steps,
                memory=state.get("memory", ""),
                task_progress=state.get("task_progress", ""),
                future_plans=state.get("future_plans", ""),
            )

            agent_prompt = CustomAgentMessagePrompt(
                state=browser_state,
                actions=state.get("tools_used", []),
                result=state.get("environment_output", {})
                .get("result", {})
                .get("action_results", []),
                include_attributes=[
                    "title",
                    "type",
                    "name",
                    "role",
                    "aria-label",
                    "placeholder",
                    "value",
                    "alt",
                ],
                max_error_length=400,
                step_info=step_info,
            )

            # Get messages using both system prompt and detailed state
            messages = [SystemMessage(content=prompt), agent_prompt.get_user_message()]

            # Use structured output without functions
            structured_llm = llm.with_structured_output(BrowserResponse)
            logger.info("BrowserEnvNode: Getting next actions from LLM")
            response = await structured_llm.ainvoke(messages)

            # Validate response
            if not response or not isinstance(response, BrowserResponse):
                logger.error(f"Invalid LLM response type: {type(response)}")
                return Command(goto="end")

            logger.debug(f"LLM Response: {response.model_dump_json(indent=2)}")

            # Update brain state from response
            state["brain"] = response.current_state.model_dump()

            # Execute actions
            results = []
            for raw_action in response.action:
                try:
                    # Get action type and parameters
                    action_type = next(iter(raw_action))
                    action_params = raw_action[action_type]

                    logger.info(f"Raw action: {raw_action}")
                    logger.info(f"Action type: {action_type}")
                    logger.info(f"Action params: {action_params}")

                    # Format for browser_use ActionModel, which expects the action type
                    # as a field name with parameters as the value
                    formatted_action = {
                        action_type: action_params  # This matches the expected format
                    }

                    logger.info(f"Formatted action for ActionModel: {formatted_action}")
                    action_model = ActionModel(**formatted_action)
                    logger.info(
                        f"Created ActionModel: {action_model.model_dump_json()}"
                    )

                    logger.info("Calling controller.act...")
                    result = await self.controller.act(
                        action_model, browser_env.browser_context
                    )
                    logger.info(
                        f"Controller.act result: {result.model_dump_json() if result else 'None'}"
                    )

                    try:
                        logger.info("Attempting page load state waits...")
                        page = browser_env.browser_context.page
                        logger.info("Got page reference")
                        await page.wait_for_load_state("networkidle")
                        logger.info("Network idle complete")
                        await page.wait_for_load_state("domcontentloaded")
                        logger.info("DOM content loaded")
                        await page.wait_for_load_state("load")
                        logger.info("Page load complete")
                    except Exception as wait_error:
                        logger.debug(f"Wait error (non-critical): {str(wait_error)}")

                    results.append(result)
                    logger.info(
                        f"Added result to results list. Total results: {len(results)}"
                    )
                except Exception as e:
                    logger.error(f"Action execution failed: {str(e)}", exc_info=True)
                    results.append(ActionResult(error=str(e)))

            # Update state
            success = all(not r.error for r in results)
            error = next((r.error for r in results if r.error), None)

            state["environment_output"] = {
                "success": success,
                "result": {"action_results": [r.model_dump() for r in results]},
                "error": error,
            }

            if error:
                logger.error(f"BrowserEnvNode: Action failed - {error}")
                self.consecutive_failures += 1
                if self.consecutive_failures > 3:
                    state["error"] = "Too many consecutive failures"
                    return Command(goto="end")
                return Command(goto="coordinator")

            # Reset failure count on success
            self.consecutive_failures = 0

            # Check completion
            if self._evaluate_task_completion(state, results):
                logger.info("BrowserEnvNode: Task complete")
                state["done"] = True
                return Command(goto="end")

            logger.info("BrowserEnvNode: Actions completed, continuing to coordinator")
            return Command(goto="coordinator")

        except Exception as e:
            logger.error(f"BrowserEnvNode: Execution error - {str(e)}", exc_info=True)
            state["error"] = str(e)
            return Command(goto="end")

    def _prepare_messages(self, state: AgentState, browser_state: Dict) -> List[Dict]:
        return [
            SystemMessage(content="You are a browser automation expert."),
            HumanMessage(content=state["task"]),
            SystemMessage(
                content=f"Current browser state:\nURL: {browser_state.get('url')}\nTitle: {browser_state.get('title')}"
            ),
        ]

    def _parse_llm_response(self, ai_message) -> List[ActionModel]:
        if not ai_message.additional_kwargs.get("function_call"):
            return []
        try:
            tool_calls = json.loads(
                ai_message.additional_kwargs["function_call"]["arguments"]
            )
            return [ActionModel(**action) for action in tool_calls.get("actions", [])]
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []

    def _evaluate_task_completion(
        self, state: AgentState, results: List[ActionResult]
    ) -> bool:
        """Enhanced task completion detection with more signals"""
        if not results:
            return False

        last_result = results[-1]

        # Check for errors
        if last_result.error:
            return False

        # Look for completion indicators in extracted content
        if last_result.extracted_content:
            completion_indicators = [
                "task complete",
                "finished",
                "done",
                "success",
                "completed successfully",
                "goal achieved",
                "found what we needed",
                "mission accomplished",
            ]
            content = last_result.extracted_content.lower()
            if any(indicator in content for indicator in completion_indicators):
                return True

        # Check for repeated actions or no progress
        if state.get("last_url") == getattr(last_result, "url", None):
            state["same_url_count"] = state.get("same_url_count", 0) + 1
            if state["same_url_count"] > 3:  # No progress after multiple attempts
                return True
        else:
            state["same_url_count"] = 0
            state["last_url"] = getattr(last_result, "url", None)

        return False
