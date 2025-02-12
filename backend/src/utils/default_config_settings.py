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
        "enable_recording": os.getenv("ENABLE_RECORDING", "False").lower() == "true",
        "window_w": int(os.getenv("RESOLUTION_WIDTH", 1920)),
        "window_h": int(os.getenv("RESOLUTION_HEIGHT", 1080)),
        "save_recording_path": os.getenv("SAVE_RECORDING_PATH", "./tmp/record_videos"),
        "save_trace_path": os.getenv("SAVE_TRACE_PATH", "./tmp/traces"),
        "save_agent_history_path": os.getenv(
            "SAVE_AGENT_HISTORY_PATH", "./tmp/agent_history"
        ),
        "task": "go to google.com and type 'OpenAI' click search and give me the first url",
    }


def load_config_from_file(config_file):
    """Load settings from a UUID.pkl file."""
    try:
        with open(config_file, "rb") as f:
            settings = pickle.load(f)
        return settings
    except Exception as e:
        return f"Error loading configuration: {str(e)}"


def save_config_to_file(settings, save_dir="./tmp/webui_settings"):
    """Save the current settings to a UUID.pkl file with a UUID name."""
    os.makedirs(save_dir, exist_ok=True)
    config_file = os.path.join(save_dir, f"{uuid.uuid4()}.pkl")
    with open(config_file, "wb") as f:
        pickle.dump(settings, f)
    return f"Configuration saved to {config_file}"


def save_current_config(*args):
    current_config = {
        "agent_type": args[0],
        "max_steps": args[1],
        "max_actions_per_step": args[2],
        "use_vision": args[3],
        "tool_calling_method": args[4],
        "llm_provider": args[5],
        "llm_model_name": args[6],
        "llm_temperature": args[7],
        "llm_base_url": args[8],
        "llm_api_key": args[9],
        "use_own_browser": args[10],
        "keep_browser_open": args[11],
        "headless": args[12],
        "disable_security": args[13],
        "enable_recording": args[14],
        "window_w": args[15],
        "window_h": args[16],
        "save_recording_path": args[17],
        "save_trace_path": args[18],
        "save_agent_history_path": args[19],
        "task": args[20],
    }
    return save_config_to_file(current_config)
