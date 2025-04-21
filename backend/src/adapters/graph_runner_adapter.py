"""GraphRunner adapter for workflow-srv integration."""

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import HTTPException

# Import workflow-srv components
from agent_workflow_server.agents.base import BaseAdapter, BaseAgent
from agent_workflow_server.services.message import Message
from agent_workflow_server.storage.models import Run

# Import our components
from src.graph.environments.manager import environment_manager
from src.graph.graph_runner import GraphRunner
from src.utils.agent_state import AgentState


class GraphRunnerAgent(BaseAgent):
    """Adapter for our GraphRunner to work with workflow-srv."""

    def __init__(self, runner: GraphRunner):
        self.runner = runner
        self._state: Dict[str, AgentState] = {}

    def convert_to_acp_message(
        self, update: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Message:
        """Convert our update format to ACP message format."""
        if update.get("type") == "error":
            return Message(
                type="message",
                event="error",
                data=str(update.get("error")),
            )
        elif update.get("type") == "approval_request":
            return Message(
                type="interrupt",
                event="approval",
                data=update.get("approval_data"),
            )
        else:
            return Message(
                type="message",
                event="update",
                data=update.get("content", update),
            )

    async def astream(self, run: Run) -> AsyncGenerator[Message, None]:
        """Stream execution results in ACP format."""
        thread_id = run["thread_id"] if "thread_id" in run else str(uuid4())
        task = run["input"].get("task", "") if "input" in run else ""

        try:
            # Initialize state for this run
            self._state[thread_id] = AgentState(task=task, thread_id=thread_id)

            # Execute graph runner with thread-specific environments
            metadata = {"thread_id": thread_id}

            async for update in self.runner.execute(task, thread_id):
                if update is None:
                    continue

                yield self.convert_to_acp_message(update, metadata)

        except Exception as e:
            yield Message(
                type="message",
                event="error",
                data=str(e),
            )
        finally:
            # Clear state
            if thread_id in self._state:
                del self._state[thread_id]


class GraphRunnerAdapter(BaseAdapter):
    """Adapter factory for GraphRunner integration."""

    def __init__(self):
        self.graph_runner = GraphRunner()

    def load_agent(self, agent: Any) -> Optional[BaseAgent]:
        """Create a GraphRunnerAgent if the agent is a GraphRunner."""
        if isinstance(agent, GraphRunner):
            return GraphRunnerAgent(runner=agent)
        return None


# Singleton instance for AGENTS_REF
graph_runner = GraphRunner()
graph_runner_instance = graph_runner  # For AGENTS_REF registration
