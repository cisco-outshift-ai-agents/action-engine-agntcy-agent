import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .base import ToolResult

logger = logging.getLogger(__name__)


class TerminalCommandAction(BaseModel):
    """Model for terminal command execution"""

    command: str = Field(..., description="The command to execute in the terminal")


@tool("terminal")
async def terminal_tool(command: str, config: RunnableConfig) -> ToolResult:
    """Execute terminal commands with persistent session state.
    Features:
    - Maintains working directory between commands
    - Handles directory navigation (cd)
    - Supports input for interactive commands
    - Manages timeouts and cleanup
    - Returns standardized output/error

    Args:
        command (str): The terminal command to execute
    """
    logger.info(f"Terminal tool called with command: {command}")

    try:
        if not command:
            return ToolResult(error="Command is required")

        terminal_manager = config["configurable"]["terminal_manager"]
        if not terminal_manager:
            return ToolResult(error="Terminal manager not initialized")

        current_terminal_id = await terminal_manager.get_current_terminal_id()
        output, success = await terminal_manager.execute_command(
            current_terminal_id, command
        )
        return ToolResult(output=output) if success else ToolResult(error=output)

    except Exception as e:
        return ToolResult(error=f"Failed to process terminal command: {str(e)}")
