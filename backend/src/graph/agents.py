"""LangGraph agent implementations with environment management."""

from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4
import os
from dataclasses import dataclass

from langchain_core.runnables import RunnableConfig
from langgraph.constants import INTERRUPT
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Command

from agent_workflow_server.agents.adapters.langgraph import LangGraphAgent
from agent_workflow_server.services.message import Message
from agent_workflow_server.storage.models import Run

from src.graph.environments.manager import environment_manager
from src.utils.utils import get_llm_model
from src.utils.agent_state import AgentState


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


class ThreadEnvironmentAgent(LangGraphAgent):
    """LangGraph agent that manages per-thread environments.

    Handles initialization and cleanup of browser, terminal and other environments
    for each execution thread. This ensures that each thread gets its own isolated
    set of environments that persist across the entire graph execution
    """

    def __init__(self, agent: CompiledGraph):
        super().__init__(agent)
        self._thread_envs: Dict[str, Dict] = {}
        self._thread_configs: Dict[str, EnvironmentConfig] = {}
        self._thread_llms: Dict[str, Any] = {}

    def _parse_config(
        self, config: Optional[Dict[str, Any]] = None
    ) -> EnvironmentConfig:
        """Parse raw config dict into EnvironmentConfig."""
        config_dict = {
            # Default LLM settings from env
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL_NAME", "gpt-4"),
            "llm_temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
        }

        # Update with provided config
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

            self._thread_envs[thread_id] = {
                "llm": self._thread_llms[thread_id],
                "browser": envs.browser_manager.browser,
                "browser_context": envs.browser_manager.browser_context,
                "dom_service": envs.browser_manager.dom_service,
                "terminal_manager": envs.terminal_manager,
                "planning_environment": envs.planning_manager,
            }

        return self._thread_envs[thread_id]

    async def astream(self, run: Run) -> AsyncIterator[Message]:
        """Stream execution results with environment management."""
        thread_id = run.get("thread_id", str(uuid4()))

        # Setup environments first
        env_config = await self.setup_environments(thread_id, run.get("config", {}))

        # Create agent state with task
        config = run.get("config", {})
        thread_config = self._thread_configs[thread_id]
        agent_state = AgentState(
            task=run["input"]["task"],
            max_steps=thread_config.max_steps,
            max_actions_per_step=thread_config.max_actions_per_step,
            tool_calling_method=thread_config.tool_calling_method,
        )

        # Add environments to config
        configurable = config.get("configurable", {})
        configurable.update(env_config)
        configurable["thread_id"] = thread_id

        # Handle interrupts
        if "interrupt" in run and "user_data" in run["interrupt"]:
            agent_state = run["interrupt"]["user_data"]
            input_data = Command(resume=agent_state)
        else:
            input_data = agent_state

        # Execute graph with environments
        async for event in self.agent.astream(
            input=input_data,
            config=RunnableConfig(
                configurable=configurable,
                tags=config.get("tags"),
                recursion_limit=config.get("recursion_limit", 25),
            ),
        ):
            for k, v in event.items():
                if k == INTERRUPT:
                    yield Message(
                        type="interrupt",
                        event=k,
                        data=v[0].value,
                    )
                else:
                    yield Message(
                        type="message",
                        event=k,
                        data=v,
                    )

    async def cleanup(self, thread_id: str):
        """Clean up environments for a thread."""
        if thread_id in self._thread_envs:
            # Clear thread state
            del self._thread_envs[thread_id]
            del self._thread_configs[thread_id]
            del self._thread_llms[thread_id]
