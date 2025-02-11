import base64
import os
import time
import logging


from pathlib import Path
from typing import Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from src.utils.gemini import CustomChatGoogleGenerativeAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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
    llm_api_key = kwargs.get("llm_api_key", "")
    logger.info("Provider: %s", provider)
    logger.info("API Key: %s", llm_api_key)

    if provider == "anthropic":
        return ChatAnthropic(
            model_name=kwargs.get("model_name", "claude-3-5-sonnet-20240620"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=kwargs.get("llm_base_url", "https://api.anthropic.com"),
            api_key=SecretStr(llm_api_key),
            timeout=kwargs.get("timeout", 60),
            stop=kwargs.get("stop", None),
        )
    elif provider == "mistral":
        return ChatMistralAI(
            model_name=kwargs.get("model_name", "mistral-large-latest"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=kwargs.get("llm_base_url"),
            api_key=SecretStr(llm_api_key),
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=kwargs.get("llm_base_url", "https://api.openai.com/v1"),
            api_key=SecretStr(llm_api_key),
        )
    elif provider == "gemini":
        llm_api_key = kwargs.get("llm_api_key")
        if not llm_api_key:
            raise ValueError("API key is missing")

        client_options = {
            "api_endpoint": kwargs.get("llm_base_url", "https://api.google.com/v1")
        }

        return ChatGoogleGenerativeAI(
            model=kwargs.get("model_name", "gemini-2.0-flash-exp"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=kwargs.get("llm_base_url", "https://api.google.com/v1"),
            api_key=SecretStr(llm_api_key),
            google_api_key=SecretStr(llm_api_key),
            client_options={
                "api_endpoint": kwargs.get("llm_base_url", "https://api.google.com/v1"),
                "api_key": llm_api_key,
            },
        )
    elif provider == "ollama":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        else:
            base_url = kwargs.get("base_url")
            return ChatOllama(
                model=kwargs.get("model_name", "qwen2.5:7b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                num_predict=kwargs.get("num_predict", 1024),
                base_url=kwargs.get("base_url", base_url),
            )
    elif provider == "azure_openai":
        return AzureChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            api_version="2024-05-01-preview",
            azure_endpoint=kwargs.get("llm_base_url", ""),
            api_key=SecretStr(llm_api_key),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Predefined model names for common providers
model_names = {
    "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "o3-mini"],
    "gemini": [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b-latest",
        "gemini-2.0-flash-thinking-exp-1219",
    ],
    "ollama": ["qwen2.5:7b", "llama2:7b"],
    "azure_openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "mistral": [
        "pixtral-large-latest",
        "mistral-large-latest",
        "mistral-small-latest",
        "ministral-8b-latest",
    ],
}


def encode_image(img_path):
    if not img_path:
        return None
    with open(img_path, "rb") as fin:
        image_data = base64.b64encode(fin.read()).decode("utf-8")
    return image_data


def get_latest_files(
    directory: str, file_types: list = [".webm", ".zip"]
) -> Dict[str, Optional[str]]:
    """Get the latest recording and trace files"""
    latest_files: Dict[str, Optional[str]] = {ext: None for ext in file_types}

    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return latest_files

    for file_type in file_types:
        try:
            matches = list(Path(directory).rglob(f"*{file_type}"))
            if matches:
                latest = max(matches, key=lambda p: p.stat().st_mtime)
                # Only return files that are complete (not being written)
                if time.time() - latest.stat().st_mtime > 1.0:
                    latest_files[file_type] = str(latest)
        except Exception as e:
            print(f"Error getting latest {file_type} file: {e}")

    return latest_files


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
