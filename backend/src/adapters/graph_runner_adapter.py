"""GraphRunner adapter for workflow-srv integration."""

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException

# Import from installed workflow-srv package
from workflow_srv.src.agent_workflow_server.agents.base import BaseAdapter, BaseAgent
from workflow_srv.src.agent_workflow_server.services.message import Message
from workflow_srv.src.agent_workflow_server.generated.models.run import Run
from workflow_srv.src.agent_workflow_server.generated.models.agent_acp_descriptor import (
    AgentACPDescriptor,
)

from src.graph.environments.terminal import TerminalManager
from src.graph.environments.browser import BrowserEnvironment
from src.graph.graph_runner import GraphRunner
from src.utils.agent_state import AgentState


class GraphRunnerAgent(BaseAgent):
    """Adapter for our GraphRunner to work with workflow-srv."""

    def __init__(
        self,
        runner: GraphRunner,
        terminal_manager: TerminalManager,
        browser_env: BrowserEnvironment,
    ):
        self.runner = runner
        self.terminal_manager = terminal_manager
        self.browser_env = browser_env
        self._state: Dict[str, AgentState] = {}

    async def initialize_environments(
        self, run: Run
    ) -> tuple[Optional[str], Optional[str]]:
        """Initialize terminal and browser environments if needed."""
        terminal_id = None
        browser_id = None

        config = run.config or {}

        # Initialize terminal if requested
        if config.get("use_terminal", True):
            try:
                terminal_id = await self.terminal_manager.create_terminal()
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to initialize terminal: {str(e)}"
                )

        # Initialize browser if requested
        if config.get("use_browser", True):
            try:
                browser_id = await self.browser_env.initialize(
                    headless=config.get("headless", True),
                    use_own_browser=config.get("use_own_browser", False),
                    keep_browser_open=config.get("keep_browser_open", True),
                )
            except Exception as e:
                # Clean up terminal if browser fails
                if terminal_id:
                    await self.terminal_manager.close_terminal(terminal_id)
                raise HTTPException(
                    status_code=500, detail=f"Failed to initialize browser: {str(e)}"
                )

        return terminal_id, browser_id

    async def cleanup_environments(
        self, terminal_id: Optional[str], browser_id: Optional[str]
    ):
        """Clean up terminal and browser environments."""
        if terminal_id:
            try:
                await self.terminal_manager.close_terminal(terminal_id)
            except Exception:
                pass  # Best effort cleanup

        if browser_id:
            try:
                await self.browser_env.cleanup(browser_id)
            except Exception:
                pass  # Best effort cleanup

    def convert_to_acp_message(
        self, update: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Message:
        """Convert our update format to ACP message format."""
        if update.get("type") == "error":
            return Message(
                role="assistant",
                content=str(update.get("error")),
                metadata={"type": "error", **metadata},
            )
        elif update.get("type") == "approval_request":
            return Message(
                role="assistant",
                content=update.get("approval_data"),
                metadata={
                    "type": "interrupt",
                    "interrupt_type": "approval",
                    **metadata,
                },
            )
        else:
            return Message(
                role="assistant",
                content=update.get("content", update),
                metadata={"type": "update", **metadata},
            )

    async def astream(self, run: Run) -> AsyncGenerator[Message, None]:
        """Stream execution results in ACP format."""
        thread_id = run.thread_id if hasattr(run, "thread_id") else str(uuid4())
        task = run.input.get("task", "") if run.input else ""

        terminal_id = None
        browser_id = None

        try:
            # Initialize environments
            terminal_id, browser_id = await self.initialize_environments(run)

            # Initialize state for this run
            self._state[thread_id] = AgentState(
                terminal_id=terminal_id, browser_id=browser_id, task=task
            )

            # Execute graph runner with environments
            metadata = {
                "terminal_id": terminal_id,
                "browser_id": browser_id,
                "thread_id": thread_id,
            }

            async for update in self.runner.execute(task, thread_id):
                if update is None:
                    continue

                yield self.convert_to_acp_message(update, metadata)

        except Exception as e:
            yield Message(role="assistant", content=str(e), metadata={"type": "error"})
        finally:
            # Cleanup environments
            await self.cleanup_environments(terminal_id, browser_id)

            # Clear state
            if thread_id in self._state:
                del self._state[thread_id]


class GraphRunnerAdapter(BaseAdapter):
    """Adapter factory for GraphRunner integration."""

    def __init__(self):
        self.terminal_manager = TerminalManager.get_instance()
        self.browser_env = BrowserEnvironment()

    def load_agent(self, agent: Any) -> Optional[BaseAgent]:
        """Create a GraphRunnerAgent if the agent is a GraphRunner."""
        if isinstance(agent, GraphRunner):
            return GraphRunnerAgent(
                runner=agent,
                terminal_manager=self.terminal_manager,
                browser_env=self.browser_env,
            )
        return None


# Singleton instances for AGENTS_REF
terminal_manager = TerminalManager.get_instance()
browser_env = BrowserEnvironment()
graph_runner = GraphRunner(terminal_manager=terminal_manager)
graph_runner_instance = graph_runner  # For AGENTS_REF registration
