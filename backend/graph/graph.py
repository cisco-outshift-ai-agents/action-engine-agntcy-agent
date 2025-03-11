from langchain_core.runnables import RunnableConfig
from langgraph.graph import Graph, StateGraph
from core.types import AgentState
from .nodes import (
    RouterNode,
    ChainOfThoughtNode,
    BrowserEnvNode,
    coordinate_environments,
)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("chain_of_thought", ChainOfThoughtNode())
    workflow.add_node("router", RouterNode())
    workflow.add_node("browser_env", BrowserEnvNode())
    workflow.add_node("coordinator", coordinate_environments)

    # Add end node that marks task as complete
    async def end_node(state: AgentState) -> AgentState:
        state["done"] = True
        return state

    workflow.add_node("end", end_node)

    # Set up agent loop with conditional edges
    workflow.add_edge("START", "chain_of_thought")
    workflow.add_edge("chain_of_thought", "router")
    workflow.add_edge("router", "browser_env")
    workflow.add_edge("browser_env", "coordinator")
    workflow.add_edge("coordinator", "chain_of_thought")

    workflow.add_conditional_edges(
        "coordinator",
        lambda state: (
            "end" if state.get("done") or state.get("error") else "chain_of_thought"
        ),
    )

    workflow.add_edge("end", "END")

    return workflow.compile()


# Create a compiled instance for direct use
agent_graph = create_agent_graph()
