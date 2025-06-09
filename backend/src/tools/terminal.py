import logging
from enum import Enum
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .base import ToolResult

logger = logging.getLogger(__name__)


class TerminalAction(str, Enum):
    """Supported terminal actions"""

    RUN = "run"
    CREATE = "create"
    SWITCH = "switch"
    CLOSE = "close"
    LIST = "list"


class TerminalToolInput(BaseModel):
    """Input model for terminal tool actions - validates required parameters for each action type"""

    action: TerminalAction = Field(
        description="The terminal action to perform. Each action has specific required parameters:\n"
        "- run: requires 'script' - executes a command in current terminal\n"
        "- create: creates new terminal session\n"
        "- switch: requires 'terminal_id' - switches to specified terminal\n"
        "- close: optional 'terminal_id' - closes specified or current terminal\n"
        "- list: no parameters - lists all active terminals"
    )
    script: Optional[str] = Field(
        None,
        description="Required for 'run' action. The command to execute in the terminal. Can be any valid shell command",
    )
    terminal_id: Optional[int] = Field(
        None,
        description="Required for 'switch' action, optional for 'close'. The ID of the terminal to switch to or close",
        ge=0,
    )
  
    model_config = {
        "json_schema_extra": {
            "required": ["action"],
            "examples": [
                {"action": "run", "script": "ls -la"},
                {"action": "create"},
                {"action": "switch", "terminal_id": 1},
                {"action": "close", "terminal_id": 1},
                {"action": "list"},
            ],
            "title": "Terminal Action Parameters",
            "description": "Parameters required for each terminal action type",
            "dependencies": {
                "run": {
                    "required": ["script"],
                    "properties": {"script": {"type": "string"}},
                },
                "switch": {
                    "required": ["terminal_id"],
                    "properties": {"terminal_id": {"type": "integer", "minimum": 0}},
                },
                "create": {
                   
                },
                "close": {
                    "properties": {"terminal_id": {"type": "integer", "minimum": 0}},
                },
                "list": {"required": []},
            },
        }
    }


@tool("terminal")
async def terminal_tool(
    action: TerminalAction,
    script: Optional[str] = None,
    terminal_id: Optional[int] = None,
    config: RunnableConfig = None,
) -> ToolResult:
    """
    Terminal interaction tool for managing multiple persistent terminal sessions.
    Each action requires specific parameters.

    REQUIRED PARAMETERS PER ACTION:
    - run: script (command to execute)
    - create: no parameters needed
    - switch: terminal_id
    - close: terminal_id (optional - defaults to current)
    - list: no parameters needed

    Features:
    - Maintains working directory between commands
    - Handles interactive commands
    - Manages multiple terminal sessions
    - Supports session naming and switching
    - Returns command output or error status

    Args:
        action: The terminal action to perform from the list above
        script: Required command string for 'run' action
        terminal_id: Required terminal ID for 'switch' action, optional for 'close'
    """
    logger.info(f"Terminal tool invoked with action: {action}")

    try:
        if not config or "configurable" not in config:
            return ToolResult(error="Config is required")

        terminal_manager = config["configurable"].get("terminal_manager")
        if not terminal_manager:
            return ToolResult(error="Terminal manager not initialized")

        # Create validated model from inputs
        params = TerminalToolInput(
            action=action,
            script=script,
            terminal_id=terminal_id,
        )

        if params.action == TerminalAction.RUN:
            if not script:
                return ToolResult(error="Script is required for 'run' action")
            current_terminal_id = await terminal_manager.get_current_terminal_id()
            output, success = await terminal_manager.execute_command(
                current_terminal_id, script
            )
            return ToolResult(output=output) if success else ToolResult(error=output)

        elif params.action == TerminalAction.CREATE:
            new_terminal_id = await terminal_manager.create_terminal()
            return ToolResult(
                output={
                    "message": f"Created new terminal session with ID: {new_terminal_id}",
                    "terminal_id": new_terminal_id
          }
            )

        elif params.action == TerminalAction.SWITCH:
            if terminal_id is None:
                return ToolResult(error="Terminal ID is required for 'switch' action")
            await terminal_manager.switch_to_terminal(terminal_id)
            return ToolResult(output=f"Switched to terminal {terminal_id}")

        elif params.action == TerminalAction.CLOSE:
            target_id = (
                terminal_id
                if terminal_id is not None
                else await terminal_manager.get_current_terminal_id()
            )
            await terminal_manager.close_terminal(target_id)
            return ToolResult(output=f"Closed terminal {target_id}")

        elif params.action == TerminalAction.LIST:
            terminals = await terminal_manager.list_terminals()
            return ToolResult(output=f"Active terminals: {terminals}")

        else:
            return ToolResult(error=f"Action {params.action} not implemented")

    except Exception as e:
        logger.info(f"Terminal action failed: {str(e)}")
        return ToolResult(error=f"Terminal action failed: {str(e)}")
