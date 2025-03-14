from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .base import ToolResult
from langchain_core.tools import tool


class TerminationStatus(str, Enum):
    """Available termination statuses"""

    SUCCESS = "success"
    FAILURE = "failure"


class TerminateInput(BaseModel):
    """Input model for termination"""

    status: TerminationStatus = Field(description="The completion status")
    reason: Optional[str] = Field(None, description="Explanation for termination")


@tool
async def terminate_tool(
    status: TerminationStatus, reason: Optional[str] = None
) -> ToolResult:
    """
    Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.
    - Use for successful task completion
    - Use for unrecoverable errors
    - Use when all requirements are met
    - Required to properly end execution chain

    Args:
        status: Completion status ("success" or "failure")
        reason: Optional explanation for termination
    """
    message = f"Interaction terminated with status: {status}"
    if reason:
        message += f"\nReason: {reason}"

    return ToolResult(output=message, system=f"Termination triggered: {status}")
