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
import base64

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import SecretStr

load_dotenv()


def get_llm_model(provider: str, **kwargs):
    """
    Get LLM model based on model name with provider prefix
    :param kwargs: Configuration parameters
    :return: LLM model instance
    """
    try:
        config = {
            "model": kwargs.get("model_name"),
            "temperature": kwargs.get("temperature", 0.0),
        }
        return init_chat_model(**config)
    except Exception as e:
        print(f"Error initializing LLM model: {e}")


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
