from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from browser_use.dom.service import DomService
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict

from src.graph.environments.planning import PlanningEnvironment
from src.graph.environments.terminal import TerminalManager

# Avoids circular imports
if TYPE_CHECKING:
    from src.browser.custom_browser import CustomBrowser
    from src.browser.custom_context import CustomBrowserContext


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


def unique_list_reducer(current_list, new_list) -> List[Dict]:
    """Extends lists while maintaining uniqueness based on id field"""
    if current_list is None:
        return new_list or []
    if new_list is None:
        return current_list

    seen = {item.get("id"): item for item in current_list if item.get("id")}
    for item in new_list:
        if item.get("id"):  # Only add items that have the id field
            seen[item["id"]] = item
    return list(seen.values())


class EnvironmentType(str, Enum):
    """Supported environment types"""

    BROWSER = "browser"
    TERMINAL = "terminal"
    CODE = "code"


class BrainState(BaseModel):
    """Captures the thought process and state evaluation"""

    prev_action_evaluation: str = Field(
        default="",
        description="Evaluation of the previous action's success or failure",
        examples=["Success", "Failure", "Unknown"],
    )
    important_contents: str = Field(
        default="",
        description="Key information extracted from the current state",
        examples=[
            "The page title is 'Wikipedia'",
            "The error message is '404 Not Found'",
            "The user's email is ...",
        ],
    )
    task_progress: str = Field(
        default="",
        description="Current progress towards completing the task.",
    )
    future_plans: str = Field(default="", description="Planned next steps or actions")
    thought: str = Field(
        default="",
        description="Current reasoning process.  This will be sent to the user.",
    )
    summary: str = Field(
        default="",
        description="Brief summary of current state and progress.  This will be sent to the user, so please keep it focused and concise.",
    )


class ActionResult(BaseModel):
    """Individual action result structure"""

    action: Dict[str, Any]
    is_done: bool = False
    error: Optional[str] = None
    extracted_content: Optional[str] = None


# TODO: (julvalen) Ensure this syncs up with the AgentOutput Pydantic model in /src/graph/manifest/models.py
# I don't know how to resolve the necessity between the Annotations in the TypedDict
# and the need for AgentOutput to be a Pydantic model.
class AgentState(TypedDict, total=False):
    """Enhanced state with brain tracking and concurrent update handling"""

    # Core state
    task: Annotated[str, last_value_reducer]
    plan: Annotated[Optional[Dict[str, Any]], last_value_reducer]

    # Brain state
    brain: Annotated[Dict[str, Any], dict_merge_reducer]
    thought: Annotated[str, last_value_reducer]
    summary: Annotated[str, last_value_reducer]
    context: Annotated[Dict[str, Any], dict_merge_reducer]

    # Memory and history
    messages: Annotated[List[Dict], last_value_reducer]
    tools_used: Annotated[List[Dict], list_extend_reducer]

    # Control flow
    error: Annotated[Optional[str], last_value_reducer]
    next_node: Annotated[Optional[str], last_value_reducer]
    exiting: Annotated[bool, last_value_reducer]

    # Tool approval management
    tool_calls: Annotated[List[Dict], last_value_reducer]
    pending_approval: Annotated[Dict[str, Any], dict_merge_reducer]

    class Config:
        """Pydantic configuration"""

        arbitrary_types_allowed = True
        extra = "allow"


def create_default_agent_state(task: str = "") -> Dict:
    """Create a default agent state with all required fields"""
    return {
        "task": task,
        "plan": None,
        "brain": {},
        "thought": "",
        "summary": "",
        "context": {},
        "messages": [],
        "tools_used": [],
        "error": None,
        "next_node": None,
        "exiting": False,
        "pending_approval": {},
        "tool_calls": [],
    }


@dataclass
class GraphConfigConfigurable:
    llm: ChatOpenAI
    browser: "CustomBrowser"
    browser_context: "CustomBrowserContext"
    dom_service: DomService
    terminal_manager: TerminalManager
    planning_environment: PlanningEnvironment


@dataclass
class GraphConfig:
    configurable: GraphConfigConfigurable


@dataclass
class WorkableToolCall:
    name: str
    args: Dict
    call_id: str
