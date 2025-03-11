import logging
import os
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
        """Execute task using LangGraph"""
        try:
            logger.info("Starting graph execution")
            logger.debug(f"Delegator exists: {self.delegator is not None}")
            logger.debug(
                f"Graph exists: {self.delegator and self.delegator.graph is not None}"
            )

            if not self.delegator:
                logger.error("Delegator is None")
                raise RuntimeError("Delegator not initialized")

            if not self.delegator.graph:
                logger.error("Graph is None")
                raise RuntimeError("Graph not initialized")

            agent_state = create_default_agent_state(task)
            logger.debug(f"Created agent state: {agent_state}")

            # Create config correctly with tools directly in configurable
            config = {
                "configurable": {
                    "llm": self.llm,
                    "env_registry": {
                        EnvironmentType.BROWSER: self.browser_env,
                    },
                }
            }

            result = await self.delegator.graph.ainvoke(agent_state, config)
            logger.info("Graph invocation successful")

            yield self._format_state_for_ui(result)

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
        """Format graph state for UI consumption with brain state"""
        brain_state = state.get("brain", {})
        return {
            "html_content": self._get_html_content(state),
            "current_state": {
                "prev_action_evaluation": brain_state.get("prev_action_evaluation", ""),
                "important_contents": brain_state.get("important_contents", ""),
                "task_progress": brain_state.get("task_progress", ""),
                "future_plans": brain_state.get("future_plans", ""),
                "thought": brain_state.get("thought", ""),
                "summary": brain_state.get("summary", ""),
            },
            "action": state.get("tools_used", []),
        }

    def _get_html_content(self, state: Dict) -> str:
        """Get HTML content from browser state if available"""
        # This will need to use browser screenshot functionality
        # from the existing implementation
        return "<h1>Processing...</h1>"
