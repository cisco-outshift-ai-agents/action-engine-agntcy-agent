import os
import pickle
import uuid

from dotenv import load_dotenv

load_dotenv()


def default_config():
    """Prepare the default configuration"""

    # TODO Turn these all into environment variables
    return {
        "max_steps": int(os.getenv("MAX_STEPS", 100)),
        "max_actions_per_step": int(os.getenv("MAX_ACTIONS_PER_STEP", 10)),
        "use_vision": os.getenv("USE_VISION", "False").lower() == "true",
        "tool_calling_method": os.getenv("TOOL_CALLING_METHOD", "auto"),
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "llm_model_name": os.getenv("LLM_MODEL_NAME", "gpt-4o"),
        "llm_temperature": float(os.getenv("LLM_TEMPERATURE", 1.0)),
        "llm_base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "llm_api_key": os.getenv("LLM_API_KEY", ""),
        "use_own_browser": os.getenv("USE_OWN_BROWSER", "False").lower() == "true",
        "keep_browser_open": os.getenv("KEEP_BROWSER_OPEN", "False").lower() == "true",
        "headless": os.getenv("HEADLESS", "False").lower() == "true",
        "disable_security": os.getenv("DISABLE_SECURITY", "False").lower() == "true",
        "window_w": int(os.getenv("RESOLUTION_WIDTH", 1920)),
        "window_h": int(os.getenv("RESOLUTION_HEIGHT", 1080)),
        "task": "go to google.com and type 'OpenAI' click search and give me the first url",
        "limit_messages": (
            int(os.getenv("LIMIT_MESSAGES"))
            if os.getenv("LIMIT_MESSAGES") not in [None, "", "None"]
            else None
        ),
    }
