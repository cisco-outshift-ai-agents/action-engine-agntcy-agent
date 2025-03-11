from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BrowserAction(BaseModel):
    """Base browser action type"""

    action_type: str = Field(description="Type of action to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )


class DoneAction(BrowserAction):
    action_type: str = "done"
    text: str = Field(..., description="Completion message")


class SearchGoogleAction(BrowserAction):
    action_type: str = "search_google"
    query: str = Field(..., description="Search query")


class GoToUrlAction(BrowserAction):
    action_type: str = "go_to_url"
    url: str = Field(..., description="URL to navigate to")


class GoBackAction(BrowserAction):
    action_type: str = "go_back"


class ClickElementAction(BrowserAction):
    action_type: str = "click_element"
    index: int = Field(..., description="Element index to click")
    xpath: Optional[str] = Field(None, description="Optional xpath selector")


class InputTextAction(BrowserAction):
    action_type: str = "input_text"
    index: int = Field(..., description="Element index to input text into")
    text: str = Field(..., description="Text to input")
    xpath: Optional[str] = Field(None, description="Optional xpath selector")


class SwitchTabAction(BrowserAction):
    action_type: str = "switch_tab"
    page_id: int = Field(..., description="Tab index to switch to")


class OpenTabAction(BrowserAction):
    action_type: str = "open_tab"
    url: str = Field(..., description="URL to open in new tab")


class ExtractContentAction(BrowserAction):
    action_type: str = "extract_content"
    include_links: bool = Field(
        False, description="Whether to include links in extracted content"
    )


class ScrollDownAction(BrowserAction):
    action_type: str = "scroll_down"
    amount: Optional[int] = Field(None, description="Pixel amount to scroll down")


class ScrollUpAction(BrowserAction):
    action_type: str = "scroll_up"
    amount: Optional[int] = Field(None, description="Pixel amount to scroll up")


class SendKeysAction(BrowserAction):
    action_type: str = "send_keys"
    keys: str = Field(..., description="Special keys or keyboard shortcuts to send")


class ScrollToTextAction(BrowserAction):
    action_type: str = "scroll_to_text"
    text: str = Field(..., description="Text to scroll to on page")


class GetDropdownOptionsAction(BrowserAction):
    action_type: str = "get_dropdown_options"
    index: int = Field(..., description="Element index of dropdown")


class SelectDropdownOptionAction(BrowserAction):
    action_type: str = "select_dropdown_option"
    index: int = Field(..., description="Element index of dropdown")
    text: str = Field(..., description="Text of option to select")


class CopyToClipboardAction(BrowserAction):
    action_type: str = "copy_to_clipboard"
    text: str = Field(..., description="Text to copy to clipboard")


class PasteFromClipboardAction(BrowserAction):
    action_type: str = "paste_from_clipboard"


def get_action_schemas() -> Dict[str, str]:
    """Get formatted documentation of all action schemas"""
    action_schemas = {}
    for cls in [
        DoneAction,
        SearchGoogleAction,
        GoToUrlAction,
        GoBackAction,
        ClickElementAction,
        InputTextAction,
        SwitchTabAction,
        OpenTabAction,
        ExtractContentAction,
        ScrollDownAction,
        ScrollUpAction,
        SendKeysAction,
        ScrollToTextAction,
        GetDropdownOptionsAction,
        SelectDropdownOptionAction,
        CopyToClipboardAction,
        PasteFromClipboardAction,
    ]:
        # Get the schema
        schema = cls.model_json_schema()

        # Extract field info
        fields = schema.get("properties", {})
        required = schema.get("required", [])

        # Format as example JSON
        example = {
            cls.__fields__["action_type"].default: {
                k: "..." for k in fields.keys() if k != "action_type" and k != "params"
            }
        }

        # Add to docs
        action_schemas[cls.__fields__["action_type"].default] = {
            "example": example,
            "description": cls.__doc__ or "",
            "required": [f for f in required if f != "action_type"],
        }

    return action_schemas


class BrowserState(BaseModel):
    """Browser state assessment and planning"""

    prev_action_evaluation: str = Field(
        description="Success|Failed|Unknown - Analysis of previous action results"
    )
    important_contents: str = Field(
        description="Important contents related to task on current page"
    )
    task_progress: str = Field(description="Numbered list of completed steps")
    future_plans: str = Field(description="Numbered list of remaining steps")
    thought: str = Field(description="Reflection on current state and next actions")
    summary: str = Field(description="Brief description of next actions")


class BrowserResponse(BaseModel):
    """Complete browser action response"""

    current_state: BrowserState
    action: List[Dict[str, Dict[str, Any]]] = Field(
        description="List of actions to execute",
        examples=[
            [
                {"go_to_url": {"url": "https://example.com"}},
                {"click_element": {"index": 1}},
                {"input_text": {"index": 2, "text": "search query"}},
                {"done": {"text": "Task completed"}},
            ]
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_state": {
                        "prev_action_evaluation": "Unknown",
                        "important_contents": "",
                        "task_progress": "",
                        "future_plans": "",
                        "thought": "Need to navigate to website",
                        "summary": "Opening webpage",
                    },
                    "action": [{"go_to_url": {"url": "https://www.wikipedia.org"}}],
                }
            ]
        }
    }
