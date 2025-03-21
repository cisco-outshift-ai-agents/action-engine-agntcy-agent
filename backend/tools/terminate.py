import logging
from enum import Enum
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .base import ToolResult

logger = logging.getLogger(__name__)


class TerminationStatus(str, Enum):
    """Available termination statuses"""

    SUCCESS = "success"
    FAILURE = "failure"


class TerminateInput(BaseModel):
    """Input model for termination"""

    status: TerminationStatus = Field(description="The completion status")
    reason: Optional[str] = Field(None, description="Explanation for termination")


@tool("terminate")
async def terminate_tool(
    status: TerminationStatus, reason: Optional[str] = None
) -> ToolResult:
    """
    Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
    - Use when the user's request is met and the interaction is complete.
    - Use when the assistant cannot proceed further with the task.

    Args:
        status: Completion status ("success" or "failure")
        reason: Optional explanation for termination
    """
    logger.info(f"Termination tool called with status: {status}")

    message = f"Interaction terminated with status: {status}"
    if reason:
        message += f"\nReason: {reason}"

    return ToolResult(output=message, system=f"Termination triggered: {status}")
