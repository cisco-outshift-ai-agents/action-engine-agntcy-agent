import logging
from typing import Optional, Any
from pydantic import Field, BaseModel
from enum import Enum
from langchain_core.runnables import RunnableConfig
from .base import ToolResult
from langchain_core.tools import tool
from browser_use.controller.service import Controller

logger = logging.getLogger(__name__)


class BrowserAction(str, Enum):
    """Supported browser actions"""

    NAVIGATE = "navigate"
    CLICK = "click"
    INPUT_TEXT = "input_text"
    SCREENSHOT = "screenshot"
    GET_HTML = "get_html"
    GET_TEXT = "get_text"
    READ_LINKS = "read_links"
    EXECUTE_JS = "execute_js"
    SCROLL = "scroll"
    SWITCH_TAB = "switch_tab"
    NEW_TAB = "new_tab"
    CLOSE_TAB = "close_tab"
    REFRESH = "refresh"


class BrowserToolInput(BaseModel):
    """Input model for browser tool actions"""

    action: BrowserAction = Field(description="The browser action to perform")
    url: Optional[str] = Field(
        None, description="URL for 'navigate' or 'new_tab' actions"
    )
    index: Optional[int] = Field(
        None, description="Element index for 'click' or 'input_text' actions"
    )
    text: Optional[str] = Field(None, description="Text for 'input_text' action")
    script: Optional[str] = Field(
        None, description="JavaScript code for 'execute_js' action"
    )
    scroll_amount: Optional[int] = Field(
        None, description="Pixels to scroll (positive for down, negative for up)"
    )
    tab_id: Optional[int] = Field(None, description="Tab ID for 'switch_tab' action")

    model_config = {
        "json_schema_extra": {
            "required": ["action"],
            "dependencies": {
                "navigate": ["url"],
                "click": ["index"],
                "input_text": ["index", "text"],
                "execute_js": ["script"],
                "switch_tab": ["tab_id"],
                "new_tab": ["url"],
                "scroll": ["scroll_amount"],
            },
        }
    }


@tool
async def browser_use_tool(
    action: BrowserAction,
    url: Optional[str] = None,
    index: Optional[int] = None,
    text: Optional[str] = None,
    script: Optional[str] = None,
    scroll_amount: Optional[int] = None,
    tab_id: Optional[int] = None,
    config: RunnableConfig = None,  # Changed to explicitly use RunnableConfig
) -> ToolResult:
    """
    Interact with web browser to perform navigation, clicking, typing and other actions.
    All actions return standardized results with success/failure status and error messages.
    Browser state is maintained between actions within the same session.

    Args:
        action: The browser action to perform
        url: URL for 'navigate' or 'new_tab' actions
        index: Element index for 'click' or 'input_text' actions
        text: Text for 'input_text' action
        script: JavaScript code for 'execute_js' action
        scroll_amount: Pixels to scroll (positive for down, negative for up)
        tab_id: Tab ID for 'switch_tab' action
    """
    try:
        if not config or "configurable" not in config:
            return ToolResult(error="Config is required")

        browser_context = config["configurable"].get("browser_context")
        if not browser_context:
            return ToolResult(error="Browser context not initialized")

        # Create validated model from inputs
        params = BrowserToolInput(
            action=action,
            url=url,
            index=index,
            text=text,
            script=script,
            scroll_amount=scroll_amount,
            tab_id=tab_id,
        )

        if params.action == BrowserAction.NAVIGATE:
            if not params.url:
                return ToolResult(error="URL is required for 'navigate' action")
            await browser_context.navigate_to(params.url)
            return ToolResult(output=f"Navigated to {params.url}")

        elif params.action == BrowserAction.CLICK:
            index = params.index
            if index is None:
                return ToolResult(error="Index is required for 'click' action")
            await browser_context._click_element_by_index(index)
            return ToolResult(output=f"Clicked element at index {index}")

        elif params.action == BrowserAction.INPUT_TEXT:
            index = params.index
            text = params.text
            if index is None or not text:
                return ToolResult(
                    error="Index and text are required for 'input_text' action"
                )
            element = await browser_context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element {index} not found")
            await browser_context._input_text_element_node(element, text)
            return ToolResult(output=f"Input '{text} at index {index}")

        elif params.action == BrowserAction.SCREENSHOT:
            screenshot = await browser_context.take_screenshot(full_page=True)
            return ToolResult(output=screenshot, system=screenshot)

        else:
            return ToolResult(error=f"Action {params.action} not implemented")

    except Exception as e:
        logger.info(f"Browser action failed: {str(e)}")
        return ToolResult(error=f"Browser action failed: {str(e)}")
