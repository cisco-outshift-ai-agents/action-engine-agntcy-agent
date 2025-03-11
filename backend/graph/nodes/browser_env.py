import json
import logging
import asyncio
from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from browser_use.agent.views import ActionModel, ActionResult
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

            # Check for task completion before execution
            if self._should_complete_task(state, response, browser_state):
                logger.info("Task completion detected, ensuring done action is present")
                if not any(
                    isinstance(action.get("done"), dict) for action in response.action
                ):
                    response.action = [
                        {"done": {"text": "Task completed successfully"}}
                    ]

            # Update brain state from response
            state["brain"] = response.current_state.model_dump()

            # Execute actions through environment adapter
            try:
                # Format actions for adapter
                actions_dict = {"action": response.action}

                # Let the adapter handle execution
                output = await browser_env.execute(actions_dict)

                # Update state with results
                state["environment_output"] = output.dict()

                if output.error:
                    logger.error(f"BrowserEnvNode: Action failed - {output.error}")
                    self.consecutive_failures += 1
                    if self.consecutive_failures > 3:
                        state["error"] = "Too many consecutive failures"
                        return Command(goto="end")
                    return Command(goto="coordinator")

                # Reset failure count on success
                self.consecutive_failures = 0

                # Check completion based on output
                if self._evaluate_task_completion(
                    state, output.result.get("action_results", [])
                ):
                    logger.info("BrowserEnvNode: Task complete")
                    state["done"] = True
                    return Command(goto="end")

                return Command(goto="coordinator")

            except Exception as e:
                logger.error(f"Action execution failed: {str(e)}", exc_info=True)
                state["error"] = str(e)
                return Command(goto="end")

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
        self, state: AgentState, results: List[Dict]  # Change type hint to Dict
    ) -> bool:
        """Enhanced task completion detection with more signals"""
        if not results:
            return False

        last_result = results[-1]

        # Check for errors using dict access instead of attribute
        if last_result.get("error"):
            return False

        # Look for completion indicators in extracted content
        if last_result.get("extracted_content"):
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
            content = last_result["extracted_content"].lower()
            if any(indicator in content for indicator in completion_indicators):
                return True

        # Check for repeated actions or no progress
        if state.get("last_url") == last_result.get("url"):
            state["same_url_count"] = state.get("same_url_count", 0) + 1
            if state["same_url_count"] > 3:  # No progress after multiple attempts
                return True
        else:
            state["same_url_count"] = 0
            state["last_url"] = last_result.get("url")

        return False

    def _should_complete_task(
        self, state: AgentState, response: BrowserResponse, browser_state
    ) -> bool:
        """Determine if task should be considered complete"""
        # Check current browser state against task requirements
        task = state.get("task", "").lower()
        current_url = getattr(browser_state, "url", "").lower()

        # Task-specific completion checks
        if "go to" in task:
            target_url = task.split("go to")[-1].strip()
            if target_url in current_url:
                # Add done action if not present
                if not any(
                    isinstance(action.get("done"), dict) for action in response.action
                ):
                    response.action.append(
                        {"done": {"text": f"Successfully navigated to {target_url}"}}
                    )
                return True

        # Check response indicators
        brain_state = response.current_state
        completion_indicators = [
            not brain_state.future_plans,
            "no further actions" in brain_state.future_plans.lower(),
            "task complete" in brain_state.thought.lower(),
            "accomplished" in brain_state.thought.lower(),
            "achieved" in brain_state.thought.lower(),
        ]

        return any(completion_indicators)
