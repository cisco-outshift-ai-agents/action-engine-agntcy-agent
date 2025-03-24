import asyncio
import logging
from dataclasses import dataclass

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import BrowserError, BrowserState, TabInfo
from browser_use.dom.service import DomService
from browser_use.dom.views import DOMBaseNode, DOMElementNode, DOMTextNode
from browser_use.utils import time_execution_sync
from playwright.async_api import BrowserContext as PlaywrightBrowserContext
from playwright.async_api import Page

from tools.utils import stringify_dom_element_node

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    context: PlaywrightBrowserContext
    current_page: Page
    cached_state: BrowserState


class CustomBrowserContext(BrowserContext):
    def __init__(
        self, browser: "Browser", config: BrowserContextConfig = BrowserContextConfig()
    ):
        super(CustomBrowserContext, self).__init__(browser=browser, config=config)

    @time_execution_sync(
        "--get_state"
    )  # This decorator might need to be updated to handle async
    async def get_state(self, use_vision: bool = False) -> BrowserState:
        """Get the current state of the browser"""
        await self._wait_for_page_and_frames_load()
        session = await self.get_session()
        session.cached_state = await self._update_state(use_vision=use_vision)

        # Save cookies if a file is specified
        if self.config.cookies_file:
            asyncio.create_task(self.save_cookies())

        return session.cached_state

    async def get_semantic_elements_string(self, element_tree: DOMElementNode) -> str:
        """Convert the processed DOM content to semantic HTML string."""
        formatted_text = []

        def process_node(node: DOMBaseNode, depth: int) -> None:
            if isinstance(node, DOMElementNode):
                # Add element with highlight_index
                if node.highlight_index is not None:
                    semantic_desc = stringify_dom_element_node(node)
                    formatted_text.append(f"{node.highlight_index}[:]<{semantic_desc}>")

                # Process children regardless
                for child in node.children:
                    process_node(child, depth + 1)

            elif isinstance(node, DOMTextNode):
                # Add text only if it doesn't have a highlighted parent
                if not node.has_parent_with_highlight_index():
                    formatted_text.append(f"_[:]{node.text}")

        process_node(element_tree, 0)
        return "\n".join(formatted_text)

    async def _update_state(
        self, use_vision: bool = False, focus_element: int = -1
    ) -> BrowserState:
        """Update and return state."""
        session = await self.get_session()
        # Check if current page is still valid, if not switch to another available page
        try:
            page = await self.get_current_page()
            await page.evaluate("console.log('evaluated')")
        except Exception as e:
            logger.debug(f"Current page is no longer accessible: {str(e)}")
            # Get all available pages
            pages = session.context.pages
            if pages:
                session.current_page = pages[-1]
                page = session.current_page
                logger.debug(f"Switched to page: {await self._get_page_title(page)}")
            else:
                raise BrowserError("Browser closed: no valid pages available")
        try:
            await self.remove_highlights()
            dom_service = DomService(page)
            content = await dom_service.get_clickable_elements(
                focus_element=focus_element,
                viewport_expansion=self.config.viewport_expansion,
                highlight_elements=self.config.highlight_elements,
            )

            screenshot_b64 = None
            if use_vision:
                screenshot_b64 = await self.take_screenshot()

            pixels_above, pixels_below = await self.get_scroll_info(page)

            title = await self._get_page_title(page)

            tabs = await self.get_tabs_info()

            self.current_state = BrowserState(
                element_tree=content.element_tree,
                selector_map=content.selector_map,
                url=page.url,
                title=title,
                tabs=tabs,
                screenshot=screenshot_b64,
                pixels_above=pixels_above,
                pixels_below=pixels_below,
            )

            return self.current_state
        except Exception as e:
            logger.error(f"Failed to update state: {str(e)}")
            # Return last known good state if available
            if hasattr(self, "current_state"):
                return self.current_state
        raise

    async def get_tabs_info(self) -> list[TabInfo]:
        """Get information about all tabs with timeout protection"""
        session = await self.get_session()
        tabs_info = []

        for page_id, page in enumerate(session.context.pages):
            # Create tab info with URL immediately
            tab_info = TabInfo(page_id=page_id, url=page.url, title="")

            # Get title with timeout protection
            tab_info.title = await self._get_page_title(page)

            tabs_info.append(tab_info)

        return tabs_info

    async def get_session(self) -> BrowserSession:
        """Lazy initialization of the browser and related components"""
        if self.session is None:
            return await self._initialize_session()
        return self.session

    async def _get_page_title(self, page: Page) -> str:
        """The page title tends to stall out, so we need to wrap it in a timeout"""
        try:
            return await asyncio.wait_for(page.title(), timeout=1.0)
        except asyncio.TimeoutError:
            return "Loading..."
