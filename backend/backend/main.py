import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.utils.default_config_settings import default_config
from webui import run_with_stream
from browser_use.agent.views import AgentHistory
from pydantic import ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

app = FastAPI(title="ActionEngine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default configuration
DEFAULT_CONFIG = default_config()


def format_update_for_ui(update):
    """Ensure the WebSocket update follows the UI's expected format."""

    if isinstance(update, list):
        return [format_update_for_ui(item) for item in update]

    if isinstance(update, AgentHistory):
        try:
            return {
                "action": [
                    {
                        "input_text": action.input_text.model_dump() if action.input_text else None,
                        "click_element": action.click_element.model_dump() if action.click_element else None,
                        "prev_action_evaluation": update.model_output.current_state.prev_action_evaluation,
                        "important_contents": update.model_output.current_state.important_contents,
                        "task_progress": update.model_output.current_state.task_progress,
                        "future_plans": update.model_output.current_state.future_plans,
                        "thought": update.model_output.current_state.thought,
                        "summary": update.model_output.current_state.summary,
                    }
                    for action in update.model_output.action
                ] if update.model_output else [],
                "current_state": {},  
                "html_content": ""  
            }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"error": "Invalid model output format"}

    elif isinstance(update, dict):
        return update  # Pass raw dictionaries through as they may be error messages

    else:
        logger.warning(f"Unexpected update format: {type(update)}")
        return {"error": "Unexpected update format"}


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat interactions."""
    logger.info("New WebSocket connection attempt")
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Client message received: {data}")

            try:
                client_payload = json.loads(data)
                task = client_payload.get("task", DEFAULT_CONFIG["task"])
                add_infos = client_payload.get("add_infos", "")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse client message: {str(e)}")
                await websocket.send_text(json.dumps({"error": str(e)}))
                continue

            # Create configuration
            config = DEFAULT_CONFIG.copy()
            config.update({"task": task, "add_infos": add_infos})

            try:
                # Process updates from the agent
                async for update in run_with_stream(**config):
                    logger.info(f"Received update: {type(update)}")
                    
                    formatted_update = format_update_for_ui(update)
                    await websocket.send_text(json.dumps(formatted_update))

            except Exception as e:
                logger.error(f"Stream processing error: {str(e)}", exc_info=True)
                await websocket.send_text(json.dumps({"error": "Stream processing failed", "details": str(e)}))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        logger.info("Closing WebSocket connection")
        await websocket.close()
