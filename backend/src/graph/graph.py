"""Graph-based execution engine."""

import logging
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, Graph, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.graph.thread_agent_wrapper import ThreadAgentWrapper
from src.graph.nodes.approval import HumanApprovalNode
from src.graph.nodes.executor import ExecutorNode
from src.graph.nodes.planning import PlanningNode
from src.graph.nodes.thinking import ThinkingNode
from src.graph.nodes.tool_generator import ToolGeneratorNode
from src.graph.types import AgentState

logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the core LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("tool_generator", ToolGeneratorNode())
    workflow.add_node("human_approval", HumanApprovalNode())
    workflow.add_node("executor", ExecutorNode())
    workflow.add_node("planning", PlanningNode())
    workflow.add_node("thinking", ThinkingNode())

    workflow.add_edge(START, "planning")

    workflow.add_conditional_edges(
        "thinking", lambda state: END if state.get("exiting") else "planning"
    )

    workflow.add_conditional_edges(
        "planning", lambda state: END if state.get("exiting") else "tool_generator"
    )

    workflow.add_edge("tool_generator", "human_approval")

    workflow.add_conditional_edges(
        "human_approval",
        lambda state: (
            END
            if state.get("exiting")
            else (
                "executor"
                if state.get("pending_approval", {}).get("approved")
                else "thinking"
            )
        ),
    )

    workflow.add_conditional_edges(
        "executor", lambda state: END if state.get("exiting") else "thinking"
    )

    # Use our custom checkpointer that handles environment objects
    from src.graph.checkpointer import EnvironmentAwareCheckpointer

    checkpointer = EnvironmentAwareCheckpointer()
    return workflow.compile(checkpointer=checkpointer)


# Create the base graph
base_graph = create_agent_graph()

# Wrap it in our ThreadEnvironmentAgent that handles environment management
action_engine_graph = ThreadAgentWrapper(base_graph)
