import logging

from langgraph.graph import END, START, Graph, StateGraph
from graph.types import AgentState
from langchain_core.runnables import RunnableConfig

from graph.nodes.executor import ExecutorNode
from graph.nodes.planning import PlanningNode


logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    workflow.add_node("executor", ExecutorNode())
    workflow.add_node("planning", PlanningNode())

    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "executor")

    workflow.add_conditional_edges(
        "executor",
        lambda state: (END if state.get("exiting") else "planning"),
    )

    logger.info(workflow)

    return workflow.compile()
