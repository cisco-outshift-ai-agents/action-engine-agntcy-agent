import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, Graph, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.graph.nodes.approval import HumanApprovalNode
from src.graph.nodes.executor import ExecutorNode
from src.graph.nodes.planning import PlanningNode
from src.graph.nodes.thinking import ThinkingNode
from src.graph.nodes.tool_generator import (
    ToolGeneratorNode,
)  # Make sure this import matches your file structure
from src.graph.types import AgentState

logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    # Add nodes - make sure names match what's in your logs
    workflow.add_node("planning", PlanningNode())
    workflow.add_node(
        "tool_selection", ToolGeneratorNode()
    )  # Use the class from your import
    workflow.add_node("human_approval", HumanApprovalNode())
    workflow.add_node("executor", ExecutorNode())
    workflow.add_node("thinking", ThinkingNode())

    # Start with planning
    workflow.add_edge(START, "planning")

    # Planning goes to tool selection
    workflow.add_edge("planning", "tool_selection")

    # Tool selection goes to human approval
    workflow.add_edge("tool_selection", "human_approval")

    # Human approval conditionally routes based on approval state
    workflow.add_conditional_edges(
        "human_approval",
        lambda state: (
            "executor"
            if state.get("pending_approval", {}).get("approved", False)
            else "thinking"
        ),
    )

    # Executor always goes to thinking
    workflow.add_edge("executor", "thinking")

    # Thinking conditionally ends or continues planning
    workflow.add_conditional_edges(
        "thinking", lambda state: END if state.get("exiting") else "planning"
    )

    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


action_engine_graph = create_agent_graph()
