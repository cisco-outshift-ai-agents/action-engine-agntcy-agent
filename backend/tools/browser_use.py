import asyncio
import logging
import os
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass
from pydantic import Field, BaseModel
from enum import Enum

from browser_use import ActionModel
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
from browser_use.dom.service import DomService
from playwright.async_api import async_playwright
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContext
from src.utils.default_config_settings import default_config
from dotenv import load_dotenv

from .base import ToolResult
from langchain_core.tools import tool

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class BrowserToolConfig:
    """Browser configuration for the tool"""

    use_own_browser: bool = False
    keep_browser_open: bool = False
    headless: bool = False
    disable_security: bool = False
    window_w: int = 1920
    window_h: int = 1080


class BrowserSession:
    """Manages browser session state"""

    def __init__(self):
        self.lock: asyncio.Lock = asyncio.Lock()
        self.browser: Optional[CustomBrowser] = None
        self.browser_context: Optional[CustomBrowserContext] = None
        self.dom_service: Optional[DomService] = None
        self.config = BrowserToolConfig(
            **{
                k: v
                for k, v in default_config().items()
                if k in BrowserToolConfig.__annotations__
            }
        )

    async def _setup_browser(self) -> None:
        """Initializes the browser and its context if not already set up."""
        extra_chromium_args = [
            f"--window-size={self.config.window_w},{self.config.window_h}"
        ]
        chrome_path = None

        if self.config.use_own_browser:
            chrome_path = os.getenv("CHROME_PATH") or None
            chrome_user_data = os.getenv("CHROME_USER_DATA")
            if chrome_user_data:
                extra_chromium_args.append(f"--user-data-dir={chrome_user_data}")

        if not self.browser:
            if not self.config.use_own_browser:
                async with async_playwright() as p:
                    try:
                        browser_instance = CustomBrowser()
                        await browser_instance._setup_browser_with_instance(
                            playwright=p
                        )
                        self.browser = browser_instance
                    except Exception:
                        self.browser = CustomBrowser(
                            config=BrowserConfig(
                                headless=self.config.headless,
                                disable_security=self.config.disable_security,
                                chrome_instance_path=chrome_path,
                                extra_chromium_args=extra_chromium_args,
                            )
                        )
            else:
                self.browser = CustomBrowser(
                    config=BrowserConfig(
                        headless=self.config.headless,
                        disable_security=self.config.disable_security,
                        chrome_instance_path=chrome_path,
                        extra_chromium_args=extra_chromium_args,
                    )
                )

        if not self.browser_context:
            self.browser_context = await self.browser.new_context(
                config=BrowserContextConfig(
                    no_viewport=False,
                    browser_window_size=BrowserContextWindowSize(
                        width=self.config.window_w, height=self.config.window_h
                    ),
                )
            )
            # Initialize DOM service
            page = await self.browser_context.get_current_page()
            self.dom_service = DomService(page)

    async def get_session(self) -> CustomBrowserContext:
        """Ensure browser initialization and return context"""
        async with self.lock:
            await self._setup_browser()
            return self.browser_context

    async def cleanup(self):
        """Clean up browser resources."""
        async with self.lock:
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
                self.dom_service = None
            if self.browser:
                await self.browser.close()
                self.browser = None

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        if self.browser or self.browser_context:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()


# Create a singleton browser session
_browser_session = BrowserSession()


async def get_browser_session() -> BrowserSession:
    return _browser_session


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

        context = await _browser_session.get_session()

        if params.action == BrowserAction.NAVIGATE:
            if not params.url:
                return ToolResult(error="URL is required for 'navigate' action")
            await context.navigate_to(params.url)
            return ToolResult(output=f"Navigated to {params.url}")

        elif params.action == BrowserAction.CLICK:
            index = params.index
            if index is None:
                return ToolResult(error="Index is required for 'click' action")
            await context._click_element_by_index(index)
            return ToolResult(output=f"Clicked element at index {index}")

        elif params.action == BrowserAction.INPUT_TEXT:
            index = params.index
            text = params.text
            if index is None or not text:
                return ToolResult(
                    error="Index and text are required for 'input_text' action"
                )
            element = await context.get_dom_element_by_index(index)
            if not element:
                return ToolResult(error=f"Element {index} not found")
            await context._input_text_element_node(element, text)
            return ToolResult(output=f"Input '{text} at index {index}")

        elif params.action == BrowserAction.SCREENSHOT:
            screenshot = await context.take_screenshot(full_page=True)
            return ToolResult(output=screenshot, system=screenshot)

        else:
            return ToolResult(error=f"Action {params.action} not implemented")

    except Exception as e:
        logger.info(f"Browser action failed: {str(e)}")
        return ToolResult(error=f"Browser action failed: {str(e)}")
