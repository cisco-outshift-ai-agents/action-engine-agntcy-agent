import base64
import os
import time
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()

PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "azure_openai": "Azure OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
}


def get_llm_model(provider: str, **kwargs):
    """
    Get LLM model
    :param provider: Model type
    :param kwargs: Additional parameters
    :return: LLM model instance
    """
    return ChatOpenAI(
        model=kwargs.get("model_name", "gpt-4o"),
        temperature=kwargs.get("temperature", 0.0),
        base_url=kwargs.get("llm_base_url", "https://api.openai.com/v1"),
        api_key=SecretStr(kwargs.get("llm_api_key")),
    )


def encode_image(img_path):
    if not img_path:
        return None
    with open(img_path, "rb") as fin:
        image_data = base64.b64encode(fin.read()).decode("utf-8")
    return image_data


async def capture_screenshot(browser_context):
    """Capture and encode a screenshot"""
    # Extract the Playwright browser instance
    playwright_browser = (
        browser_context.browser.playwright_browser
    )  # Ensure this is correct.

    # Check if the browser instance is valid and if an existing context can be reused
    if playwright_browser and playwright_browser.contexts:
        playwright_context = playwright_browser.contexts[0]
    else:
        return None

    # Access pages in the context
    pages = None
    if playwright_context:
        pages = playwright_context.pages

    # Use an existing page or create a new one if none exist
    if pages:
        active_page = pages[0]
        for page in pages:
            if page.url != "about:blank":
                active_page = page
    else:
        return None

    # Take screenshot
    try:
        screenshot = await active_page.screenshot(type="jpeg", quality=75, scale="css")
        encoded = base64.b64encode(screenshot).decode("utf-8")
        return encoded
    except Exception as e:
        return None
