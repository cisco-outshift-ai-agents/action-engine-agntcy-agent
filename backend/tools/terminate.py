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
    Signal that an interaction flow should terminate. Used in two scenarios:
    1. SUCCESS: The requested task has been completed successfully
    2. FAILURE: The task cannot be completed due to errors or limitations

    Examples:
        Success termination:
        ```python
        {
            "status": "success",
            "reason": "Successfully created new user profile"
        }
        ```

        Failure termination:
        ```python
        {
            "status": "failure",
            "reason": "Required file not found: config.json"
        }
        ```

    Args:
        status: Must be either "success" or "failure"
        reason: Required explanation for why the flow is terminating
    """
    logger.info(f"Terminate tool called with status: {status}, reason: {reason}")

    if not isinstance(status, TerminationStatus):
        return ToolResult(
            error=f"Invalid status. Must be one of: {[s.value for s in TerminationStatus]}"
        )

    if not reason:
        return ToolResult(
            error="Reason is required - must explain why the flow is terminating"
        )

    message = f"Flow terminated - {status.upper()}\nReason: {reason}"
    return ToolResult(output=message, system={"status": status, "reason": reason})
