"""LangGraph agent implementations with environment management."""

import logging
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4
import os
from dataclasses import dataclass

from langchain_core.runnables import RunnableConfig
from langgraph.constants import INTERRUPT
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from agent_workflow_server.agents.adapters.langgraph import LangGraphAgent
from agent_workflow_server.services.message import Message
from agent_workflow_server.storage.models import Run

from src.graph.environments.manager import environment_manager
from src.utils.utils import get_llm_model
from src.utils.agent_state import AgentState
from src.graph.utils import serialize_graph_response, handle_interrupt


@dataclass
class EnvironmentConfig:
    """Configuration for thread environments."""

    # LLM Settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None

    # Browser settings
    use_browser: bool = True
    use_own_browser: bool = False
    keep_browser_open: bool = True
    headless: bool = False
    window_w: int = 1920
    window_h: int = 1080
    disable_security: bool = True

    # Terminal settings
    use_terminal: bool = True

    # Task settings
    task: str = ""
    max_steps: int = 100
    max_actions_per_step: int = 10
    tool_calling_method: str = "auto"


class ThreadEnvironmentAgent(CompiledGraph):
    """LangGraph agent that manages per-thread environments.

    Inherits from CompiledGraph to be compatible with workflow_srv's adapter.
    """

    def __init__(self, graph: CompiledGraph):
        self.graph = graph
        self._thread_envs: Dict[str, Dict] = {}
        self._thread_configs: Dict[str, EnvironmentConfig] = {}
        self._thread_llms: Dict[str, Any] = {}

    def _parse_config(
        self, config: Optional[Dict[str, Any]] = None
    ) -> EnvironmentConfig:
        """Parse raw config dict into EnvironmentConfig."""
        config_dict = {
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL_NAME", "gpt-4"),
            "llm_temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
        }
        if config:
            config_dict.update(config)
        return EnvironmentConfig(
            **{
                k: config_dict.get(k, getattr(EnvironmentConfig, k))
                for k in EnvironmentConfig.__annotations__
            }
        )

    async def initialize_llm(self, thread_id: str, config: EnvironmentConfig):
        """Initialize LLM for a thread."""
        self._thread_llms[thread_id] = get_llm_model(
            provider=config.llm_provider,
            model_name=config.llm_model,
            temperature=config.llm_temperature,
            llm_base_url=config.llm_base_url,
            llm_api_key=config.llm_api_key,
        )

    async def setup_environments(
        self, thread_id: str, config: Dict[str, Any] = None
    ) -> Dict:
        """Initialize environments for a thread if not already setup."""
        if thread_id not in self._thread_envs:
            # Parse and store config
            thread_config = self._parse_config(config)
            self._thread_configs[thread_id] = thread_config

            # Initialize LLM
            await self.initialize_llm(thread_id, thread_config)

            # Initialize environments
            envs = await environment_manager.get_or_create(thread_id)
            await envs.initialize(
                {
                    "window_w": thread_config.window_w,
                    "window_h": thread_config.window_h,
                    "headless": thread_config.headless,
                    "use_own_browser": thread_config.use_own_browser,
                    "keep_browser_open": thread_config.keep_browser_open,
                    "disable_security": thread_config.disable_security,
                }
            )

            # Store thread environments
            self._thread_envs[thread_id] = {
                "llm": self._thread_llms[thread_id],
                "browser": envs.browser_manager.browser,
                "browser_context": envs.browser_manager.browser_context,
                "dom_service": envs.browser_manager.dom_service,
                "terminal_manager": envs.terminal_manager,
                "planning_environment": envs.planning_manager,
            }

        return self._thread_envs[thread_id]

    async def ainvoke(
        self, state: Any, config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """Implements CompiledGraph's ainvoke interface."""
        if isinstance(state, dict):
            thread_id = state.get("thread_id", str(uuid4()))
            env_config = await self.setup_environments(thread_id, config)

            if config:
                config.setdefault("configurable", {})
                config["configurable"].update(env_config)
                config["configurable"]["thread_id"] = thread_id

            result = await self.graph.ainvoke(state, config)
            return result
        return await self.graph.ainvoke(state, config)

    async def astream(
        self, state: Any, config: Optional[RunnableConfig] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Implements CompiledGraph's astream interface."""
        if isinstance(state, dict):
            thread_id = state.get("thread_id", str(uuid4()))
            env_config = await self.setup_environments(thread_id, config)

            if config:
                config.setdefault("configurable", {})
                config["configurable"].update(env_config)
                config["configurable"]["thread_id"] = thread_id

            async for event in self.graph.astream(state, config):
                yield event
        else:
            async for event in self.graph.astream(state, config):
                yield event

    async def cleanup(self, thread_id: str):
        """Clean up environments for a thread."""
        if thread_id in self._thread_envs:
            await environment_manager.cleanup(thread_id)
            del self._thread_envs[thread_id]
            del self._thread_configs[thread_id]
            del self._thread_llms[thread_id]
