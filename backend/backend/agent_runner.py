import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from browser_use import ActionModel
from browser_use.agent.views import AgentHistory, AgentOutput
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextWindowSize
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from src.agent.custom_agent import CustomAgent
from src.agent.custom_prompts import CustomAgentMessagePrompt, CustomSystemPrompt
from src.agent.custom_views import CustomAgentOutput
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import BrowserContextConfig as CustomContextConfig
from src.controller.custom_controller import CustomController
from src.utils import utils
from src.utils.agent_state import AgentState
from src.utils.utils import capture_screenshot

load_dotenv()
logger = logging.getLogger(__name__)


# --- Configuration Data Classes --- #


@dataclass
class LLMConfig:
    provider: str
    model_name: str
    temperature: float
    base_url: str
    api_key: str


@dataclass
class AgentConfig:
    use_own_browser: bool
    keep_browser_open: bool
    headless: bool
    disable_security: bool
    window_w: int
    window_h: int
    task: str
    add_infos: str
    max_steps: int
    use_vision: bool
    max_actions_per_step: int
    tool_calling_method: str
    limit_messages: Optional[int]


@dataclass
class AgentResult:
    final_result: str
    errors: str
    model_actions: str
    model_thoughts: str
    latest_video: Optional[str]


# --- Agent Runner Class --- #


class AgentRunner:
    def __init__(self):
        self.browser: Optional[CustomBrowser] = None
        self.browser_context = None
        self.agent_state = AgentState()

    async def stop_agent(self) -> str:
        """Request the agent to stop and return a status message."""
        try:
            self.agent_state.request_stop()
            message = "Stop requested - the agent will halt at the next safe point"
            logger.info(f"🛑 {message}")
            return message
        except Exception as e:
            error_msg = f"Error during stop: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _setup_browser(self, agent_config: AgentConfig) -> None:
        """Initializes the browser and its context if not already set up."""
        extra_chromium_args = [
            f"--window-size={agent_config.window_w},{agent_config.window_h}"
        ]
        chrome_path = None

        if agent_config.use_own_browser:
            chrome_path = os.getenv("CHROME_PATH") or None
            chrome_user_data = os.getenv("CHROME_USER_DATA")
            if chrome_user_data:
                extra_chromium_args.append(f"--user-data-dir={chrome_user_data}")

        if not self.browser:
            if not agent_config.use_own_browser:
                async with async_playwright() as p:
                    try:
                        custom_browser_instance = CustomBrowser()
                        await custom_browser_instance._setup_browser_with_instance(
                            playwright=p
                        )
                        self.browser = custom_browser_instance
                    except Exception:
                        self.browser = CustomBrowser(
                            config=BrowserConfig(
                                headless=agent_config.headless,
                                disable_security=agent_config.disable_security,
                                chrome_instance_path=chrome_path,
                                extra_chromium_args=extra_chromium_args,
                            )
                        )
            else:
                self.browser = CustomBrowser(
                    config=BrowserConfig(
                        headless=agent_config.headless,
                        disable_security=agent_config.disable_security,
                        chrome_instance_path=chrome_path,
                        extra_chromium_args=extra_chromium_args,
                    )
                )

        if not self.browser_context:
            self.browser_context = await self.browser.new_context(
                config=CustomContextConfig(
                    no_viewport=False,
                    browser_window_size=BrowserContextWindowSize(
                        width=agent_config.window_w, height=agent_config.window_h
                    ),
                )
            )

    async def initialize_browser(self, agent_config: AgentConfig) -> None:
        """Public method to initialize the browser on server startup."""
        await self._setup_browser(agent_config)
        logger.info("Browser initialized on startup.")

    # Change from returning a tuple of final results to an async generator tha streams AgentHistory in real-time.
    async def execute_agent_core(
        self, llm, agent_config: AgentConfig
    ) -> AsyncGenerator[AgentHistory, None]:
        """
         Core execution: sets up and runs the agent,
        returning (final_result, errors, model_actions, model_thoughts).
        """
        try:
            self.agent_state.clear_stop()
            await self._setup_browser(agent_config)

            controller = CustomController()
            agent = CustomAgent(
                task=agent_config.task,
                add_infos=agent_config.add_infos,
                use_vision=agent_config.use_vision,
                llm=llm,
                browser=self.browser,
                browser_context=self.browser_context,
                controller=controller,
                system_prompt_class=CustomSystemPrompt,
                agent_prompt_class=CustomAgentMessagePrompt,
                max_actions_per_step=agent_config.max_actions_per_step,
                agent_state=self.agent_state,
                tool_calling_method=agent_config.tool_calling_method,
                limit_messages=agent_config.limit_messages,
            )

            # Stream updates from agent.run()
            async for history_item in agent.run(max_steps=agent_config.max_steps):
                yield history_item

        except Exception as e:
            logger.error(f"Error during agent run: {str(e)}", exc_info=True)
            yield {"error": str(e)}
        finally:
            if not agent_config.keep_browser_open:
                await self.close_browser()

    async def execute_agent_with_browser(
        self, llm_config: LLMConfig, agent_config: AgentConfig
    ) -> AsyncGenerator[AgentHistory, None]:
        """
        Executes the agent with browser-related logic.
        Returns AgentResult in real-time.
        """
        self.agent_state.clear_stop()

        llm = utils.get_llm_model(
            provider=llm_config.provider,
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            llm_base_url=llm_config.base_url,
            llm_api_key=llm_config.api_key,
        )

        logger.info("Starting agent execution: Streaming AgentHistory")
        # stream updates using AgentHistory
        async for history_item in self.execute_agent_core(llm, agent_config):
            yield history_item

    async def stream_agent_updates(
        self, llm_config: LLMConfig, agent_config: AgentConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
         Streams agent updates to the UI.
         Yields output as received from the agent.:
        [html_content, final_result, errors, model_actions, model_thoughts]
        """
        stream_vw = 80
        stream_vh = int(80 * agent_config.window_h // agent_config.window_w)
        if not agent_config.headless:
            html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Using browser...</h1>"
            try:
                # execute_agent_with_browser calls agent.run() and yield results as received
                async for history_item in self.execute_agent_with_browser(
                    llm_config, agent_config
                ):
                    if self.agent_state.is_stop_requested():
                        break
                    formatted_update = {
                        "html_content": html_content,
                        "current_state": {},
                        "action": [],
                    }

                    if (
                        isinstance(history_item, AgentHistory)
                        and history_item.model_output is not None
                        and isinstance(
                            history_item.model_output, (AgentOutput, CustomAgentOutput)
                        )
                    ):
                        brain = history_item.model_output.current_state
                        actions: List[Dict[str, Any]] = []

                        for action in history_item.model_output.action:
                            if isinstance(action, ActionModel):
                                formatted_action = action.model_dump(exclude_unset=True)
                                formatted_action.update(
                                    {
                                        "prev_action_evaluation": brain.prev_action_evaluation,
                                        "important_contents": brain.important_contents,
                                        "task_progress": brain.task_progress,
                                        "future_plans": brain.future_plans,
                                        "thought": brain.thought,
                                        "summary": brain.summary,
                                    }
                                )

                                actions.append(formatted_action)
                        formatted_update["action"] = actions
                    elif isinstance(history_item, AgentHistory) and history_item.result:
                        formatted_update["action"] = [
                            {
                                "summary": (
                                    history_item.result[0].extracted_content
                                    if history_item.result[0].extracted_content
                                    else ""
                                ),
                                "thought": (
                                    history_item.result[0].error
                                    if history_item.result[0].error
                                    else ""
                                ),
                                "done": history_item.result[0].is_done,
                            }
                        ]
                        logger.info(f"Formatted update being sent to UI")
                    yield formatted_update
            except Exception as e:
                err_msg = f"Agent error: {str(e)}"
                yield {
                    "html_content": html_content,
                    "current_state": {},
                    "action": [{"summary": err_msg}],
                }

                # Headless mode
        else:
            self.agent_state.clear_stop()
            agent_task = asyncio.create_task(
                self.execute_agent_with_browser(llm_config, agent_config)
            )
            html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Using browser...</h1>"
            final_result = errors = model_actions = model_thoughts = ""

            while not agent_task.done():
                try:
                    encoded_screenshot = await capture_screenshot(self.browser_context)
                    if encoded_screenshot:
                        logger.info("Screenshot captured")
                        html_content = (
                            f'<img src="data:image/jpeg;base64,{encoded_screenshot}" '
                            f'style="width:{stream_vw}vw; height:{stream_vh}vh; border:1px solid #ccc;">'
                        )
                    else:
                        html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>"
                except Exception:
                    html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>"

                if self.agent_state.is_stop_requested():
                    yield [
                        html_content,
                        final_result,
                        errors,
                        model_actions,
                        model_thoughts,
                    ]
                    break
                else:
                    yield [
                        html_content,
                        final_result,
                        errors,
                        model_actions,
                        model_thoughts,
                    ]
                await asyncio.sleep(0.05)

            try:
                yield [
                    html_content,
                    final_result,
                    errors,
                    model_actions,
                    model_thoughts,
                ]
            except Exception as e:
                err_msg = f"Agent error: {str(e)}"
                yield [html_content, "", err_msg, "", "", None, None, None]

    async def close_browser(self) -> None:
        """Closes the browser context and the browser itself."""
        if self.browser_context:
            await self.browser_context.close()
            self.browser_context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
