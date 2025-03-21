import logging
from typing import Dict, List, Optional

from src.agent.custom_views import CustomAgentStepInfo

logger = logging.getLogger(__name__)


class TerminalMessageManager:
    """Manages tracking of terminal executions"""

    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.last_terminal_id: Optional[str] = None
        self.last_output: str = ""
        self.last_working_directory: str = ""

    def add_state_message(
        self,
        terminal_id: str,
        output: str,
        working_directory: str,
        step_info: Optional[CustomAgentStepInfo] = None,
    ) -> None:
        """Store terminal state for tracking execution context"""
        state_message = {
            "terminal_id": terminal_id,
            "output": output,
            "working_directory": working_directory,
            "step_info": step_info,
        }
        self.history.append(state_message)

        # Update last known terminal state
        self.last_terminal_id = terminal_id
        self.last_output = output
        self.last_working_directory = working_directory

    def get_last_state(self) -> Dict[str, str]:
        """Retrieve the last known terminal state"""
        return {
            "terminal_id": self.last_terminal_id or "unknown",
            "output": self.last_output,
            "working_directory": self.last_working_directory,
        }

    def remove_last_state(self) -> None:
        """Remove the last terminal state when it's no longer needed"""
        if self.history:
            self.history.pop()
        if self.history:
            last_state = self.history[-1]
            self.last_terminal_id = last_state["terminal_id"]
            self.last_output = last_state["output"]
            self.last_working_directory = last_state["working_directory"]
        else:
            self.last_terminal_id = None
            self.last_output = ""
            self.last_working_directory = ""
