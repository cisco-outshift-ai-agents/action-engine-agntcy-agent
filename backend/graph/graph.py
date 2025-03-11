import logging
from langchain_core.runnables import RunnableConfig
from langgraph.graph import Graph, StateGraph, START, END
from core.types import AgentState
from .nodes import (
    RouterNode,
    ChainOfThoughtNode,
    BrowserEnvNode,
    coordinate_environments,
)

logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("chain_of_thought", ChainOfThoughtNode())
    workflow.add_node("router", RouterNode())
    workflow.add_node("browser_env", BrowserEnvNode())
    workflow.add_node("coordinator", coordinate_environments)

    # Basic flow
    workflow.add_edge(START, "chain_of_thought")
    workflow.add_edge("chain_of_thought", "router")
    workflow.add_edge("router", "browser_env")
    workflow.add_edge("browser_env", "coordinator")

    # Single conditional edge using environment_output.is_done
    workflow.add_conditional_edges(
        "coordinator",
        lambda state: (
            END
            if state.get("environment_output", {}).get("is_done") or state.get("error")
            else "chain_of_thought"
        ),
    )

    workflow.add_edge("end", END)
    return workflow.compile()


# Create a compiled instance for direct use
agent_graph = create_agent_graph()
