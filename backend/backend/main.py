import json
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.utils.default_config_settings import default_config
from webui import run_with_stream

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


@app.get("/status")
async def status():
    return {"status": "ok"}


# WebSocker endpoint for chat interactions
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
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
                logger.info(f"Extracted task: {task}")
                logger.info(f"Extracted additional info: {add_infos}")
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse client message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_text(json.dumps({"error": error_msg}))
                continue

            # Create configuration by merging defaults with client values
            config = DEFAULT_CONFIG.copy()
            config.update({"task": task, "add_infos": add_infos})

            try:
                #pass through the agent updates
                async for update in run_with_stream(**config):
                    logger.info(f"received update: {type(update)}")
                    if isinstance(update, dict):
              
                        await websocket.send_text(json.dumps(update))
                        logger.info(f"Successfully sent update to client")

                    else:
                        # Handle error cases
                        logger.warning(f"Unexpected update format: {type(update)}")
                        if isinstance(update, dict) and "error" in update:
                            await websocket.send_text(json.dumps(update))

            except Exception as stream_error:
                logger.error(f"Stream processing error: {str(stream_error)}", exc_info=True)
                await websocket.send_text(json.dumps({
                    "error": "Stream processing failed",
                    "details": str(stream_error)
                }))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {str(e)}", exc_info=True)
    finally:
        logger.info("Closing WebSocket connection")
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {str(e)}")