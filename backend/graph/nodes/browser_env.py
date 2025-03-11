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

logger = logging.getLogger(__name__)


class BrowserEnvNode:
    """Handles browser environment execution with agent-like behavior"""

    def __init__(self):
        self.name = "browser_env"
        self.controller = Controller()
        self.max_retries = 3
        self.consecutive_failures = 0

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
                "tabs": getattr(browser_state, "tabs", []),
            }

            # Use proper browser prompt
            prompt = get_browser_prompt(
                task=state["task"],
                elements=state_dict["elements"],
                current_url=state_dict["url"],
                tabs=state_dict["tabs"],
            )

            structured_llm = llm.with_structured_output(BrowserResponse)
            messages = [SystemMessage(content=prompt)]

            # Get response with proper schema
            logger.info("BrowserEnvNode: Getting next actions from LLM")
            response = await structured_llm.ainvoke(messages)

            # Update brain state from response
            state["brain"] = response.current_state.model_dump()

            # Execute actions
            results = []
            for action in response.action:
                try:
                    # Convert to ActionModel
                    action_model = ActionModel(**action)
                    result = await self.controller.act(
                        action_model, browser_env.browser_context
                    )
                    await browser_env.browser_context.wait_for_idle()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Action execution failed: {str(e)}")
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
                state["error"] = error
                return Command(goto="end")

            return Command(goto="coordinator")

        except Exception as e:
            logger.error(f"BrowserEnvNode: Execution error - {str(e)}")
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
