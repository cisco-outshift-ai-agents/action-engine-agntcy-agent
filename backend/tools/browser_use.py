import logging
from typing import Optional, Any
from pydantic import Field, BaseModel
from enum import Enum
from langchain_core.runnables import RunnableConfig
from .base import ToolResult
from langchain_core.tools import tool
from src.browser.custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)

MAX_LENGTH = 2000


class BrowserAction(str, Enum):
    """Supported browser actions"""

    NAVIGATE = "navigate"
    CLICK = "click"
    INPUT_TEXT = "input_text"
    SCREENSHOT = "screenshot"
    GET_HTML = "get_html"
    GET_TEXT = "get_text"
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
        None,
        description="Element index for 'click' or 'input_text' actions. (e.g. for 33[:]<button>, the index is 33)",
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
                "screenshot": [],
                "get_html": [],
                "get_text": [],
                "execute_js": ["script"],
                "scroll": ["scroll_amount"],
                "switch_tab": ["tab_id"],
                "new_tab": ["url"],
                "close_tab": [],
                "refresh": [],
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
    logger.info(f"Browser tool invoked with action: {action}")

    try:
        if not config or "configurable" not in config:
            return ToolResult(error="Config is required")

        browser_context = config["configurable"].get("browser_context")
        if not isinstance(browser_context, CustomBrowserContext):
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
            if not url:
                return ToolResult(error="URL is required for 'navigate' action")
            await browser_context.navigate_to(url)
            return ToolResult(output=f"Navigated to {url}")

        elif params.action == BrowserAction.CLICK:
            if index is None:
                return ToolResult(error="Index is required for 'click' action")
            element = await browser_context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element with index {index} not found")
            download_path = await browser_context._click_element_node(element)
            output = f"Clicked element at index {index}"
            if download_path:
                output += f" - Downloaded file to {download_path}"
            return ToolResult(output=output)

        elif params.action == BrowserAction.INPUT_TEXT:
            if index is None or not text:
                return ToolResult(
                    error="Index and text are required for 'input_text' action"
                )
            element = await browser_context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element with index {index} not found")
            await browser_context._input_text_element_node(element, text)
            return ToolResult(output=f"Input '{text}' into element at index {index}")

        elif params.action == BrowserAction.SCREENSHOT:
            screenshot = await browser_context.take_screenshot(full_page=True)
            return ToolResult(output=screenshot, system=screenshot)

        elif params.action == BrowserAction.GET_HTML:
            html = await browser_context.get_page_html()
            truncated = html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
            return ToolResult(output=truncated)

        elif params.action == BrowserAction.GET_TEXT:
            text = await browser_context.execute_javascript("document.body.innerText")
            return ToolResult(output=text)

        elif params.action == BrowserAction.EXECUTE_JS:
            if not params.script:
                return ToolResult(
                    error="JavaScript code is required for 'execute_js' action"
                )
            result = await browser_context.execute_javascript(params.script)
            return ToolResult(output=result)

        elif params.action == BrowserAction.SCROLL:
            if not params.scroll_amount:
                return ToolResult(error="Scroll amount is required for 'scroll' action")
            await browser_context.execute_javascript(
                f"window.scrollBy(0, {scroll_amount});"
            )
            direction = "down" if scroll_amount > 0 else "up"
            return ToolResult(
                output=f"Scrolled {direction} by {abs(scroll_amount)} pixels"
            )

        elif params.action == BrowserAction.SWITCH_TAB:
            if tab_id is None:
                return ToolResult(error="Tab ID is required for 'switch_tab' action")
            await browser_context.switch_to_tab(tab_id)
            return ToolResult(output=f"Switched to tab {tab_id}")

        elif params.action == BrowserAction.NEW_TAB:
            if not url:
                return ToolResult(error="URL is required for 'new_tab' action")
            await browser_context.create_new_tab(url)
            return ToolResult(output=f"Opened new tab with URL {url}")

        elif action == "close_tab":
            await browser_context.close_current_tab()
            return ToolResult(output="Closed current tab")

        elif action == "refresh":
            await browser_context.refresh_page()
            return ToolResult(output="Refreshed current page")

        else:
            return ToolResult(error=f"Action {params.action} not implemented")

    except Exception as e:
        logger.info(f"Browser action failed: {str(e)}")
        return ToolResult(error=f"Browser action failed: {str(e)}")
