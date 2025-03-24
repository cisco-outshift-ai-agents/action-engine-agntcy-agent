import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, Graph, StateGraph

from src.graph.nodes.executor import ExecutorNode
from src.graph.nodes.planning import PlanningNode
from src.graph.nodes.thinking import ThinkingNode
from src.graph.types import AgentState

logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    workflow.add_node("executor", ExecutorNode())
    workflow.add_node("planning", PlanningNode())
    workflow.add_node("thinking", ThinkingNode())

    workflow.add_edge(START, "planning")

    workflow.add_conditional_edges(
        "thinking",
        lambda state: (END if state.get("exiting") else "planning"),
    )

    workflow.add_conditional_edges(
        "planning",
        lambda state: (END if state.get("exiting") else "executor"),
    )

    workflow.add_conditional_edges(
        "executor",
        lambda state: (END if state.get("exiting") else "thinking"),
    )

    return workflow.compile()


action_engine_graph = create_agent_graph()
