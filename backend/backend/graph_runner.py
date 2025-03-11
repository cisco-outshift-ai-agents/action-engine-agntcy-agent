import logging
import os
import json
import asyncio
from typing import Dict, Any, AsyncIterator

from core.delegator import EnvironmentDelegator, create_default_agent_state
from core.interfaces import EnvironmentType, SharedContext
from environments.browser.adapter import BrowserEnvironmentAdapter
from .agent_runner import AgentConfig
from src.utils.utils import get_llm_model

logger = logging.getLogger(__name__)


class GraphRunner:
    """Manages execution of the LangGraph agent system while maintaining browser state"""

    def __init__(self):
        logger.info("Initializing GraphRunner...")
        # Initialize core components
        self.browser_env = BrowserEnvironmentAdapter()
        self.llm = None
        self.delegator = None  # Initialize to None first

        try:
            self.delegator = EnvironmentDelegator(llm=None)
            logger.info(
                f"Created delegator, graph present: {self.delegator.graph is not None}"
            )

            self.delegator.shared_context = SharedContext(
                task_description="",
                current_environment=EnvironmentType.BROWSER,
                agent_state=create_default_agent_state(),
            )
        except Exception as e:
            logger.error(f"Failed to create delegator: {str(e)}", exc_info=True)
            raise

    async def initialize(self, agent_config: AgentConfig) -> None:
        """Initialize environments and graph with LLM"""
        logger.info("Initializing GraphRunner with agent config")
        # Initialize LLM first
        self.llm = get_llm_model(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model_name=os.getenv("LLM_MODEL_NAME", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 1.0)),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
        )

        # Update delegator with LLM
        self.delegator.llm = self.llm

        # Register environments
        self.delegator.register_environment(EnvironmentType.BROWSER, self.browser_env)

        # Initialize shared context with config
        self.delegator.shared_context.global_memory.update(
            {
                "headless": agent_config.headless,
                "disable_security": agent_config.disable_security,
                "window_w": agent_config.window_w,
                "window_h": agent_config.window_h,
            }
        )

        # Initialize environments
        await self.delegator.initialize_environments()

    async def execute(self, task: str) -> AsyncIterator[Dict[str, Any]]:
        """Execute task using LangGraph with proper streaming"""
        try:
            logger.info("Starting graph execution with streaming")

            if not self.delegator or not self.delegator.graph:
                raise RuntimeError("Graph not initialized")

            agent_state = create_default_agent_state(task)
            config = {
                "configurable": {
                    "llm": self.llm,
                    "env_registry": {EnvironmentType.BROWSER: self.browser_env},
                }
            }

            # Use astream and properly await the async generator
            async for step_output in self.delegator.graph.astream(agent_state, config):
                logger.info(f"Stream output: {json.dumps(step_output, indent=2)}")
                # Skip empty states
                if not step_output:
                    continue
                response = self._format_state_for_ui(step_output)
                if response:  # Only yield non-None responses
                    yield response

        except Exception as e:
            logger.error(f"Graph execution error: {str(e)}", exc_info=True)
            yield {"error": str(e)}

    async def stop_agent(self) -> dict:
        """Stop the agent execution"""
        try:
            # Signal to environments to stop
            if self.delegator:
                await self.delegator.cleanup()

            stop_response = {
                "summary": "Stopped",
                "stopped": True,
            }
            return stop_response
        except Exception as e:
            error_msg = f"Error during stop: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _format_state_for_ui(self, state: Dict) -> Dict[str, Any]:
        """Enhanced state formatting for UI with streaming support"""
        # Only process browser_env node outputs
        if isinstance(state, dict) and len(state) == 1:
            node_name, node_value = next(iter(state.items()))
            if node_name != "browser_env" or node_value is None:
                return None
            node_state = node_value
        else:
            return None

        brain_state = node_state.get("brain", {})
        environment_output = node_state.get("environment_output", {})

        # Skip if no meaningful state to send
        if not brain_state and not environment_output:
            return None

        # Format actions array
        actions = []

        # Add brain state action if it has content
        brain_action = {
            "thought": brain_state.get("thought", ""),
            "summary": brain_state.get("summary", ""),
            "task_progress": brain_state.get("task_progress", ""),
            "future_plans": brain_state.get("future_plans", ""),
            "important_contents": brain_state.get("important_contents", ""),
            "prev_action_evaluation": brain_state.get("prev_action_evaluation", ""),
        }
        if any(brain_action.values()):
            actions.append(brain_action)

        # Add latest environment action if present
        if environment_output and environment_output.get("result", {}).get(
            "action_results"
        ):
            latest_action = environment_output["result"]["action_results"][-1]
            if latest_action:
                actions.append(
                    {
                        **latest_action["action"],
                        "is_done": environment_output.get("is_done", False),
                    }
                )

        # Add completion marker if environment reports done
        if environment_output.get("is_done"):
            actions.append(
                {
                    "done": True,
                    "thought": brain_state.get(
                        "thought",
                        "I have completed the requested task! Let me know if you need anything else.",
                    ),
                    "summary": brain_state.get(
                        "summary", "Task completed successfully"
                    ),
                }
            )

        if not actions:
            return None

        return {
            "html_content": self._get_html_content(node_state),
            "current_state": {
                **brain_state,
                "todo_list": node_state.get("todo_list") or "",
            },
            "action": actions,
        }

    def _get_html_content(self, state: Dict) -> str:
        """Get HTML content from browser state if available"""
        # This will need to use browser screenshot functionality
        # from the existing implementation
        return "<h1>Processing...</h1>"
