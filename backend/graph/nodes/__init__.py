import logging

from typing import Any, Dict, Optional
from langgraph.graph import END, START, Graph, StateGraph
from core.types import AgentState, BrainState, EnvironmentOutput
from langchain_core.runnables import RunnableConfig

from .chain_of_thought import ChainOfThoughtNode
from .coordinator import coordinate_environments
from .executor import ExecutorNode
from .planning import PlanningNode

logger = logging.getLogger(__name__)


def create_agent_graph(config: RunnableConfig = None) -> Graph:
    """Creates the main agent workflow graph with agent loop behavior"""
    workflow = StateGraph(AgentState)

    # Add nodes
    # workflow.add_node("chain_of_thought", ChainOfThoughtNode())
    # workflow.add_node("router", RouterNode())
    # workflow.add_node("browser_env", BrowserEnvNode())
    workflow.add_node("executor", ExecutorNode())
    workflow.add_node("planning", PlanningNode())

    # Basic flow
    # workflow.add_edge(START, "chain_of_thought")
    # workflow.add_edge("chain_of_thought", "router")
    # workflow.add_edge("chain_of_thought", "browser_env")
    # workflow.add_edge("browser_env", "coordinator")

    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "executor")

    workflow.add_conditional_edges(
        "executor",
        lambda state: (END if state.get("exiting") else "planning"),
    )

    # Single conditional edge using environment_output.is_done
    # workflow.add_conditional_edges(
    #     "coordinator",
    #     lambda state: (
    #         END
    #         if state.get("environment_output", {}).get("is_done") or state.get("error")
    #         else "chain_of_thought"
    #     ),
    # )

    logger.info(workflow)

    return workflow.compile()
