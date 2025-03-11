from typing import Dict, List, Optional, Any
from typing_extensions import TypedDict, Annotated
from enum import Enum
from pydantic import BaseModel


# Reducer functions
def last_value_reducer(current_val, new_val):
    """Keeps the last value"""
    return new_val


def dict_merge_reducer(current_dict, new_dict):
    """Merges dictionary values"""
    if current_dict is None:
        return new_dict
    if new_dict is None:
        return current_dict
    result = current_dict.copy()
    result.update(new_dict)
    return result


def list_extend_reducer(current_list, new_list):
    """Extends lists"""
    if current_list is None:
        return new_list
    if new_list is None:
        return current_list
    return current_list + new_list


class EnvironmentType(str, Enum):
    """Supported environment types"""

    BROWSER = "browser"
    TERMINAL = "terminal"
    CODE = "code"


class BrainState(BaseModel):
    """Captures the thought process and state evaluation"""

    prev_action_evaluation: str = ""
    important_contents: str = ""
    task_progress: str = ""
    future_plans: str = ""
    thought: str = ""
    summary: str = ""


class ActionResult(BaseModel):
    """Individual action result structure"""

    action: Dict[str, Any]
    is_done: bool = False
    error: Optional[str] = None
    extracted_content: Optional[str] = None


class EnvironmentOutput(BaseModel):
    """Standardized output from environment execution"""

    success: bool = True
    next_env: Optional[str] = None
    error: Optional[str] = None
    is_done: bool = False
    result: Dict[str, Any] = {"action_results": []}


class AgentState(TypedDict, total=False):
    """Enhanced state with brain tracking and concurrent update handling"""

    # Core state
    task: Annotated[str, last_value_reducer]  # Now mutable with reducer
    current_env: Annotated[str, last_value_reducer]

    # Brain state
    brain: Annotated[Dict[str, Any], dict_merge_reducer]
    thought: Annotated[str, last_value_reducer]
    summary: Annotated[str, last_value_reducer]

    # Task tracking
    task_analysis: Annotated[Dict[str, Any], dict_merge_reducer]
    context: Annotated[Dict[str, Any], dict_merge_reducer]

    # Memory and history
    messages: Annotated[List[Dict], list_extend_reducer]
    tools_used: Annotated[List[Dict], list_extend_reducer]
    environment_output: Annotated[EnvironmentOutput, last_value_reducer]

    # Control flow
    error: Annotated[Optional[str], last_value_reducer]
    next_node: Annotated[Optional[str], last_value_reducer]
    done: Annotated[bool, last_value_reducer]

    class Config:
        """Pydantic configuration"""

        arbitrary_types_allowed = True
        extra = "allow"


def create_default_agent_state(task: str = "") -> Dict:
    """Create a default agent state with all required fields"""
    return {
        "task": task,
        "current_env": "browser_env",
        "brain": {},
        "thought": "",
        "summary": "",
        "task_analysis": {},
        "context": {},
        "messages": [],
        "tools_used": [],
        "environment_output": EnvironmentOutput().model_dump(),  # Initialize with empty model
        "error": None,
        "next_node": None,
        "done": False,
    }
