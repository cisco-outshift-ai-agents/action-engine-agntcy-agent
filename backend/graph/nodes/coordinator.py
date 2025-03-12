from typing import Dict
from langgraph.types import Command
from core.types import AgentState, EnvironmentOutput
import logging
import json

logger = logging.getLogger(__name__)


async def coordinate_environments(state: AgentState) -> AgentState:
    """Coordinates transitions between environments"""
    logger.info("Coordinator: Processing state")
    logger.info(f"State contains {len(state.get('messages', []))} messages")

    # Get environment output
    env_output_dict = state.get("environment_output", {})
    try:
        output = EnvironmentOutput.model_validate(env_output_dict)
    except Exception as e:
        logger.error("Invalid environment output: %s", str(e))
        output = EnvironmentOutput()

    # Check completion state
    if output.is_done or (
        output.result.get("action_results", [])
        and output.result["action_results"][-1].get("is_done")
    ):
        logger.info("Task completion detected")
        state["done"] = True
        return state

    # Always return state to preserve it
    if output.model_dump() != env_output_dict:
        state["environment_output"] = output.model_dump()

    # Ensure messages persist
    if "messages" not in state:
        state["messages"] = []

    return state
