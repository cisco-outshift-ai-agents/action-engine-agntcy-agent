import asyncio
import logging
import os

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
from browser_use.dom.service import DomService
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from src.browser.custom_browser import CustomBrowser

load_dotenv()
logger = logging.getLogger(__name__)


class BrowserEnvironment:
    """Manages browser session state as a singleton"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserEnvironment, cls).__new__(cls)
            cls._instance.lock = asyncio.Lock()
            cls._instance.browser = None
            cls._instance.browser_context = None
            cls._instance.dom_service = None
        return cls._instance

    async def initialize(self, window_w: int = 1920, window_h: int = 1080) -> None:
        """Initialize browser resources"""
        async with self.lock:
            if self.browser:
                return

            extra_chromium_args = [f"--window-size={window_w},{window_h}"]
            chrome_path = os.getenv("CHROME_PATH") or None

            if chrome_path:
                chrome_user_data = os.getenv("CHROME_USER_DATA")
                if chrome_user_data:
                    extra_chromium_args.append(f"--user-data-dir={chrome_user_data}")

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
                                headless=False,
                                disable_security=True,
                                chrome_instance_path=chrome_path,
                                extra_chromium_args=extra_chromium_args,
                            )
                        )

            self.browser_context = await self.browser.new_context(
                config=BrowserContextConfig(
                    no_viewport=False,
                    browser_window_size=BrowserContextWindowSize(
                        width=window_w, height=window_h
                    ),
                    disable_security=True,
                )
            )

            # Initialize DOM service
            page = await self.browser_context.get_current_page()
            self.dom_service = DomService(page)

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        async with self.lock:
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
                self.dom_service = None
            if self.browser:
                await self.browser.close()
                self.browser = None

    def __del__(self):
        """Ensure cleanup when object is destroyed"""
        if self.browser or self.browser_context:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()
