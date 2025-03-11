import json
import logging
import asyncio
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from browser_use.agent.views import ActionModel
from core.types import AgentState, EnvironmentType, EnvironmentOutput, ActionResult
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
        self.max_retries = 3
        self.consecutive_failures = 0
        self.step_number = 0
        self.max_steps = 100  # Default value, could be made configurable

    async def __call__(self, state: AgentState, config: Dict):
        return await self.ainvoke(state, config)

    async def ainvoke(self, state: AgentState, config: Dict) -> AgentState:
        logger.info("BrowserEnvNode: Starting execution")
        llm = config.get("configurable", {}).get("llm")
        env_registry = config.get("configurable", {}).get("env_registry", {})
        browser_env = env_registry.get(EnvironmentType.BROWSER)

        if not browser_env or not llm:
            logger.error("BrowserEnvNode: Missing required components")
            state["error"] = "Missing required components"
            return state

        try:
            # Add delay to allow page to load
            if browser_env.browser_context:
                try:
                    page = await browser_env.browser_context.get_current_page()
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception as e:
                    logger.warning(f"Load state wait failed (non-critical): {e}")

            browser_state = await browser_env.browser_context.get_state(use_vision=True)

            # Verify we have actual content
            if not browser_state or (
                getattr(browser_state, "url", "") == "about:blank"
                and browser_env.browser_context
            ):
                logger.info("Detected blank state, retrying state fetch...")
                await asyncio.sleep(1)  # Short delay
                browser_state = await browser_env.browser_context.get_state(
                    use_vision=True
                )

            state_dict = {
                "url": getattr(browser_state, "url", ""),
                "title": getattr(browser_state, "title", ""),
                "elements": getattr(browser_state, "elements", []),
                "tabs": _convert_tabs_to_dict(getattr(browser_state, "tabs", [])),
            }

            logger.info(f"Current browser state URL: {state_dict['url']}")
            logger.info(f"Element count: {len(state_dict['elements'])}")

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

            logger.debug(f"LLM Response: {response.model_dump_json(indent=2)}")

            # Check for task completion from LLM response
            if any(isinstance(action.get("done"), dict) for action in response.action):
                logger.info("LLM indicated task completion with done action")
                output = await browser_env.execute({"action": response.action})
                output_dict = output.model_dump()

                # Create proper environment output
                env_output = EnvironmentOutput(
                    success=True,
                    is_done=True,
                    result={
                        "action_results": [
                            {
                                "action": response.action[0],
                                "is_done": True,
                                "error": None,
                                "extracted_content": output_dict.get(
                                    "extracted_content"
                                ),
                            }
                        ]
                    },
                )

                return Command(
                    update={
                        "environment_output": env_output.model_dump(),
                        "brain": response.current_state.model_dump(),
                    },
                    goto="coordinator",
                )

            # Update brain state from response
            state["brain"] = response.current_state.model_dump()

            # Execute actions through environment adapter
            try:
                output = await browser_env.execute({"action": response.action})
                output_dict = output.model_dump()

                env_output = EnvironmentOutput(
                    success=True,
                    is_done=output_dict.get("is_done", False),
                    result={
                        "action_results": [
                            {
                                "action": response.action[0],
                                "is_done": output_dict.get("is_done", False),
                                "error": output_dict.get("error"),
                                "extracted_content": output_dict.get(
                                    "extracted_content"
                                ),
                            }
                        ]
                    },
                )

                return Command(
                    update={
                        "environment_output": env_output.model_dump(),
                        "brain": response.current_state.model_dump(),
                    },
                    goto="coordinator",
                )

            except Exception as e:
                logger.error(f"Action execution failed: {str(e)}", exc_info=True)
                state["error"] = str(e)
                return state

        except Exception as e:
            logger.error(f"BrowserEnvNode: Execution error - {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state

    def _prepare_messages(self, state: AgentState, browser_state: Dict) -> List[Dict]:
        return [
            SystemMessage(content="You are a browser automation expert."),
            HumanMessage(content=state["task"]),
            SystemMessage(
                content=f"Current browser state:\nURL: {browser_state.get('url')}\nTitle: {browser_state.get('title')}"
            ),
        ]
