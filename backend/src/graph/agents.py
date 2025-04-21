"""LangGraph agent implementations with environment management."""

from typing import AsyncIterator, Dict, Optional
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.constants import INTERRUPT
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Command

from agent_workflow_server.agents.adapters.langgraph import LangGraphAgent
from agent_workflow_server.services.message import Message
from agent_workflow_server.storage.models import Run

from src.graph.environments.manager import environment_manager


class ThreadEnvironmentAgent(LangGraphAgent):
    """LangGraph agent that manages per-thread environments.

    Handles initialization and cleanup of browser, terminal and other environments
    for each execution thread. This ensures that each thread gets its own isolated
    set of environments that persist across the entire graph execution including
    interrupt handling.
    """

    def __init__(self, agent: CompiledGraph):
        super().__init__(agent)
        self._thread_envs: Dict[str, Dict] = {}

    async def setup_environments(self, thread_id: str) -> Dict:
        """Initialize environments for a thread if not already setup."""
        if thread_id not in self._thread_envs:
            envs = await environment_manager.get_or_create(thread_id)
            await envs.initialize(
                {
                    "window_w": 1920,
                    "window_h": 1080,
                    "headless": False,
                    "use_own_browser": False,
                    "keep_browser_open": True,
                    "disable_security": True,
                }
            )

            self._thread_envs[thread_id] = {
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
        env_config = await self.setup_environments(thread_id)

        # Get input and config
        input_data = run["input"]
        config = run.get("config", {})
        configurable = config.get("configurable", {})

        # Add environments to config
        configurable.update(env_config)
        configurable["thread_id"] = thread_id

        # Handle interrupts
        if "interrupt" in run and "user_data" in run["interrupt"]:
            input_data = Command(resume=run["interrupt"]["user_data"])

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
            await environment_manager.cleanup(thread_id)
            del self._thread_envs[thread_id]
