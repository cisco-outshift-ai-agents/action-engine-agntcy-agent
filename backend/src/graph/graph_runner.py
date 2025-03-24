import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from pydantic import BaseModel

from src.graph.environments.browser import BrowserSession
from src.graph.environments.planning import PlanningEnvironment
from src.graph.environments.terminal import TerminalManager
from src.graph.global_configurable import context
from src.graph.graph import action_engine_graph
from src.graph.types import (
    AgentState,
    BrainState,
    GraphConfig,
    create_default_agent_state,
)
from src.utils.utils import get_llm_model

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

    def __init__(self, terminal_manager: TerminalManager):
        self.llm = None
        self.browser_session = BrowserSession()
        self.terminal_manager = terminal_manager or TerminalManager()
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
        self.graph = action_engine_graph

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
                step_output: Dict[str, AgentState]

                yield serialize_graph_response(step_output)

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


def serialize_graph_response(data: dict[str, Any]) -> dict[str, Any]:
    """Convert pydantic models to dict for serialization"""

    if isinstance(data, BaseModel):
        return data.model_dump()

    elif isinstance(data, dict):
        return {key: serialize_graph_response(value) for key, value in data.items()}

    elif isinstance(data, list):
        return [serialize_graph_response(item) for item in data]

    return data
