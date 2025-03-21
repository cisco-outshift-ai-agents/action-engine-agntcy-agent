from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TerminalCommandAction(BaseModel):
    """Model for terminal command execution"""

    command: str = Field(..., description="The command to execute in the terminal")


class TerminalState(BaseModel):
    """Model for terminal state"""

    terminal_id: str
    output: str
    working_directory: str
