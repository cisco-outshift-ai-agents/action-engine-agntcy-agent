from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class BrowserAction(BaseModel):
    """Base class for browser actions"""

    pass


class DoneAction(BrowserAction):
    text: str = Field(
        ..., description="Completion message with any relevant extracted information"
    )


class SearchGoogleAction(BrowserAction):
    query: str = Field(..., description="Search query to execute")


class GoToUrlAction(BrowserAction):
    url: str = Field(..., description="URL to navigate to")


class GoBackAction(BrowserAction):
    pass


class ClickElementAction(BrowserAction):
    index: int = Field(..., description="Element index to click")
    xpath: Optional[str] = Field(None, description="Optional xpath selector")


class InputTextAction(BrowserAction):
    index: int = Field(..., description="Element index to input text into")
    text: str = Field(..., description="Text to input")
    xpath: Optional[str] = Field(None, description="Optional xpath selector")


class SwitchTabAction(BrowserAction):
    page_id: int = Field(..., description="Tab index to switch to")


class OpenTabAction(BrowserAction):
    url: str = Field(..., description="URL to open in new tab")


class ExtractContentAction(BrowserAction):
    include_links: bool = Field(
        False, description="Whether to include links in extracted content"
    )


class ScrollDownAction(BrowserAction):
    amount: Optional[int] = Field(None, description="Pixel amount to scroll down")


class ScrollUpAction(BrowserAction):
    amount: Optional[int] = Field(None, description="Pixel amount to scroll up")


class SendKeysAction(BrowserAction):
    keys: str = Field(..., description="Special keys or keyboard shortcuts to send")


class ScrollToTextAction(BrowserAction):
    text: str = Field(..., description="Text to scroll to on page")


class GetDropdownOptionsAction(BrowserAction):
    index: int = Field(..., description="Element index of dropdown")


class SelectDropdownOptionAction(BrowserAction):
    index: int = Field(..., description="Element index of dropdown")
    text: str = Field(..., description="Text of option to select")


class CopyToClipboardAction(BrowserAction):
    text: str = Field(..., description="Text to copy to clipboard")


class PasteFromClipboardAction(BrowserAction):
    pass


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
    action: List[Dict[str, Dict[str, Any]]]
