from typing import Dict
from langgraph.types import Command
from core.types import AgentState
import logging

logger = logging.getLogger(__name__)


async def coordinate_environments(state: AgentState) -> Dict:
    """Coordinates transitions between environments"""
    logger.info("Coordinator: Processing state")
    output = state.get("environment_output", {})

    if state.get("error"):
        logger.error(f"Coordinator: Error detected - {state['error']}")
        return Command(goto="end")

    if state.get("done"):
        logger.info("Coordinator: Task marked as done")
        return Command(goto="end")

    if output.get("error"):
        logger.error(f"Coordinator: Environment error - {output['error']}")
        state["error"] = output["error"]
        return Command(goto="end")

    if output.get("next_env"):
        logger.info(f"Coordinator: Switching to environment {output['next_env']}")
        state["current_env"] = output["next_env"]
        return Command(goto="router")

    if output.get("success"):
        logger.info("Coordinator: Action successful, continuing execution")
        return Command(goto="browser_env")

    logger.info("Coordinator: Continuing to browser environment")
    return Command(goto="browser_env")
