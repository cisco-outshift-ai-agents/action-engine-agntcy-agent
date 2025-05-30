# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
import logging
from enum import Enum
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.browser.custom_context import CustomBrowserContext
from src.tools.utils import stringify_dom_element_node

from .base import ToolResult

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
    """Input model for browser tool actions - validates required parameters for each action type"""

    action: BrowserAction = Field(
        description="The browser action to perform. Each action has specific required parameters:\n"
        "- navigate, new_tab: requires 'url'\n"
        "- click: requires 'index'\n"
        "- input_text: requires both 'index' and 'text'\n"
        "- execute_js: requires 'script'\n"
        "- scroll: requires 'scroll_amount'\n"
        "- switch_tab: requires 'tab_id'\n"
        "- screenshot, get_html, get_text, close_tab, refresh: no additional parameters needed"
    )
    url: Optional[str] = Field(
        None,
        description="Required URL for 'navigate' and 'new_tab' actions. Must be a valid HTTP/HTTPS URL",
        pattern="^https?://.*",
    )
    index: Optional[int] = Field(
        None,
        description="Required element index for 'click' and 'input_text' actions. Found in browser view as N[:]<element>, e.g. 42[:]<button>",
        ge=0,
    )
    text: Optional[str] = Field(
        None,
        description="Required text to input for 'input_text' action. The text that will be typed into the selected element",
    )
    script: Optional[str] = Field(
        None,
        description="Required JavaScript code for 'execute_js' action. Will be executed in the browser context",
    )
    scroll_amount: Optional[int] = Field(
        None,
        description="Required for 'scroll' action. Positive numbers scroll down, negative scroll up. Unit is pixels",
    )
    tab_id: Optional[int] = Field(
        None,
        description="Required tab ID for 'switch_tab' action. Must be a valid tab ID from an open browser tab",
        ge=0,
    )

    model_config = {
        "json_schema_extra": {
            "required": ["action"],
            "examples": [
                {"action": "navigate", "url": "https://www.example.com"},
                {"action": "click", "index": 42},
                {"action": "input_text", "index": 42, "text": "Hello World"},
            ],
            "title": "Browser Action Parameters",
            "description": "Parameters required for each browser action type",
            "dependencies": {
                # Required URL actions
                "navigate": {
                    "required": ["url"],
                    "properties": {"url": {"type": "string", "format": "uri"}},
                },
                "new_tab": {
                    "required": ["url"],
                    "properties": {"url": {"type": "string", "format": "uri"}},
                },
                # Required index actions
                "click": {
                    "required": ["index"],
                    "properties": {"index": {"type": "integer", "minimum": 0}},
                },
                # Required multiple parameter actions
                "input_text": {
                    "required": ["index", "text"],
                    "properties": {
                        "index": {"type": "integer", "minimum": 0},
                        "text": {"type": "string"},
                    },
                },
                # Required script actions
                "execute_js": {
                    "required": ["script"],
                    "properties": {"script": {"type": "string"}},
                },
                # Required scroll actions
                "scroll": {
                    "required": ["scroll_amount"],
                    "properties": {"scroll_amount": {"type": "integer"}},
                },
                # Required tab actions
                "switch_tab": {
                    "required": ["tab_id"],
                    "properties": {"tab_id": {"type": "integer", "minimum": 0}},
                },
                # No-parameter actions
                "screenshot": {"required": []},
                "get_html": {"required": []},
                "get_text": {"required": []},
                "close_tab": {"required": []},
                "refresh": {"required": []},
            },
        }
    }


@tool(
    "browser_use",
)
async def browser_use_tool(
    action: BrowserAction,
    url: Optional[str] = None,
    index: Optional[int] = None,
    text: Optional[str] = None,
    script: Optional[str] = None,
    scroll_amount: Optional[int] = None,
    tab_id: Optional[int] = None,
    config: RunnableConfig = None,
) -> ToolResult:
    """
    Browser automation tool for web interactions. Each action requires specific parameters.

    REQUIRED PARAMETERS PER ACTION:
    - navigate: url
    - click: index
    - input_text: index, text
    - screenshot: (no parameters needed)
    - get_html: (no parameters needed)
    - get_text: (no parameters needed)
    - execute_js: script
    - scroll: scroll_amount
    - switch_tab: tab_id
    - new_tab: url
    - close_tab: (no parameters needed)
    - refresh: (no parameters needed)

    Element indexes are shown in the browser view like: 42[:]<button>

    Args:
        action: The browser action to perform from the list above
        url: Required URL for 'navigate' and 'new_tab' actions
        index: Required element index for 'click' and 'input_text' actions (e.g. 42 from 42[:]<button>)
        text: Required text to input for 'input_text' action
        script: Required JavaScript code for 'execute_js' action
        scroll_amount: Required pixels to scroll for 'scroll' action (positive for down, negative for up)
        tab_id: Required tab ID for 'switch_tab' action
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

            # Get element and validate it exists
            element = await browser_context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element with index {index} not found")

            # Check for file uploader
            is_uploader = False
            try:
                is_uploader = await browser_context.is_file_uploader(element)
            except Exception:
                pass

            if is_uploader:
                return ToolResult(
                    error=f"Element {index} is a file upload input. Use appropriate file upload function instead."
                )

            # Track initial tab count
            initial_tab_count = len((await browser_context.get_tabs_info()))

            try:
                # Get element text before clicking in case of navigation
                element_text = element.get_all_text_till_next_clickable_element(
                    max_depth=2
                )
                logger.debug(f"Element xpath: {element.xpath}")
                logger.debug(f"Element text: {element_text}")

                try:
                    # Perform click and capture download info
                    download_path = await browser_context._click_element_node(element)

                    # Build success message
                    if download_path:
                        message = f"Downloaded file to {download_path}"
                    else:
                        message = f"Clicked element with text: {element_text}"

                    # Check for new tab after successful click
                    try:
                        current_tab_count = len((await browser_context.get_tabs_info()))
                        if current_tab_count > initial_tab_count:
                            message += " - New tab opened"
                            await browser_context.switch_to_tab(-1)
                    except Exception as tab_error:
                        # Don't fail if we can't check tabs - navigation might have happened
                        logger.debug(
                            f"Tab check failed (likely due to navigation): {tab_error}"
                        )

                    return ToolResult(output=message)

                except Exception as click_error:
                    if "context was destroyed" in str(click_error):
                        # Navigation likely occurred - treat as success
                        return ToolResult(
                            output=f"Clicked element that triggered navigation: {element_text}"
                        )
                    raise  # Re-raise other click errors

            except Exception as e:
                logger.warning(f"Click failed: {str(e)}")
                return ToolResult(error=str(e))

        elif params.action == BrowserAction.INPUT_TEXT:
            if index is None or not text:
                return ToolResult(
                    error="Index and text are required for 'input_text' action"
                )
            element = await browser_context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element with index {index} not found")
            await browser_context._input_text_element_node(element, text)
            return ToolResult(
                output=f"Input '{text}' into element at index {index} ({stringify_dom_element_node(element)})"
            )

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
        logger.error(
            f"Browser action failed - Type: {type(e)}, Value: {repr(e)}, Raw: {e}"
        )
        # If it's just a number, wrap it in a more descriptive error
        if isinstance(e, (int, str)) and str(e).isdigit():
            return ToolResult(error=f"Click operation returned unexpected value: {e}")
        return ToolResult(error=str(e))
