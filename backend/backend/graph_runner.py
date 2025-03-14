import logging
import os

from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from src.utils.utils import get_llm_model
from graph.environments.terminal import TerminalManager
from graph.global_configurable import context
from graph.nodes import create_agent_graph
from graph.environments.browser import BrowserSession
from graph.types import create_default_agent_state, GraphConfig
from graph.environments.planning import PlanningEnvironment

logger = logging.getLogger(__name__)


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
    limit_num_image_per_llm_call: Optional[int]


class GraphRunner:
    """Manages execution of the LangGraph agent system while maintaining global resources"""

    def __init__(self):
        self.llm = None
        self.browser_session = BrowserSession()
        self.terminal_manager = TerminalManager()
        self.planning_env = PlanningEnvironment()
        self.graph = None

    async def initialize(self, agent_config: AgentConfig) -> None:
        """Initialize global resources and LLM"""
        logger.debug("Initializing GraphRunner with agent config")

        # Initialize LLM and store in both places
        self.llm = get_llm_model(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model_name=os.getenv("LLM_MODEL_NAME", "gpt-4o"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 1.0)),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
        )
        context.llm = self.llm

        # Initialize graph
        self.graph = create_agent_graph()

        # Initialize browser session
        await self.browser_session.initialize(
            window_w=agent_config.window_w,
            window_h=agent_config.window_h,
        )

        # Store resources in context
        context.browser = self.browser_session.browser
        context.browser_context = self.browser_session.browser_context
        context.dom_service = self.browser_session.dom_service
        context.terminal_manager = self.terminal_manager
        context.planning_environment = self.planning_env

    async def execute(self, task: str) -> AsyncIterator[Dict[str, Any]]:
        """Execute task using LangGraph with proper streaming"""
        try:
            logger.info("Starting graph execution with streaming")

            if not self.llm:
                raise RuntimeError("LLM not initialized")

            agent_state = create_default_agent_state(task)
            config: GraphConfig = {
                "configurable": {
                    "llm": self.llm,
                    "browser": context.browser,
                    "browser_context": context.browser_context,
                    "dom_service": context.dom_service,
                    "terminal_manager": context.terminal_manager,
                    "planning_environment": context.planning_environment,
                }
            }

            # Use astream and properly await the async generator
            async for step_output in self.graph.astream(agent_state, config):
                # logger.info(f"Stream output: {json.dumps(step_output, indent=2)}")
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
            await self.cleanup()

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
            "html_content": "",
            "current_state": {
                **brain_state,
                "todo_list": node_state.get("todo_list") or "",
            },
            "action": actions,
        }

    async def cleanup(self) -> None:
        """Cleanup global resources"""
        await self.browser_session.cleanup()
        await self.terminal_manager.delete_terminal()

        # Clear context
        context.browser = None
        context.browser_context = None
        context.dom_service = None
        context.terminal_manager = None
        context.planning_environment = None
