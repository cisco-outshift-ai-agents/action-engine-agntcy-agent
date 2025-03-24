import asyncio
import logging
import subprocess
import time

import requests
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContextConfig
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import Playwright

from .custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)


class CustomBrowser(Browser):
    async def new_context(
        self, config: BrowserContextConfig = BrowserContextConfig()
    ) -> CustomBrowserContext:
        return CustomBrowserContext(config=config, browser=self)

    async def _setup_browser_with_instance(
        self, playwright: Playwright
    ) -> PlaywrightBrowser:
        """Sets up and returns a Playwright Browser instance with anti-detection measures."""
        if not self.config.chrome_instance_path:
            raise ValueError("Chrome instance path is required")

        try:
            # Check if browser is responding to /json/version
            response = requests.get("http://localhost:9222/json/version", timeout=2)
            if response.status_code == 200:
                logger.info("Found existing Chrome instance, attempting to connect")

                try:
                    browser = await playwright.chromium.connect_over_cdp(
                        endpoint_url="http://localhost:9222", timeout=2000
                    )
                    logger.info("Successfully connected to Chrome instance")
                    return browser
                except Exception as connect_error:
                    logger.warning(
                        f"Connection failed despite /json/version response: {connect_error}"
                    )
                    # Fall through to starting new Chrome instance
        except requests.ConnectionError:
            logger.info("No Chrome instance found")

        # If we get here, either no Chrome was running or connection failed
        logger.info(f"Starting new Chrome instance")
        await asyncio.create_subprocess_exec(
            "./start-chrome.sh",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        await asyncio.sleep(1)  # Give Chrome time to initialize

        # Poll to connect again after starting a new instance
        start_time = time.time()
        # Poll for 20 seconds
        while time.time() - start_time < 20:
            try:
                logger.info(
                    f"Attempting to connect to new Chrome instance at 'http://localhost:9222'"
                )
                browser = await playwright.chromium.connect_over_cdp(
                    endpoint_url="http://localhost:9222",
                    timeout=3000,
                )
                logger.info("Successfully connected to new Chrome instance")
                return browser
            except Exception as e:
                pass

        error_msg = f"Failed to connect to Chrome"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
