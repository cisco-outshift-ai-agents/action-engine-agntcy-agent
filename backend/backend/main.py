import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_runner import AgentConfig
from backend.graph_runner import GraphRunner
from src.utils.default_config_settings import default_config

logging.basicConfig(
    level=logging.INFO,  # Overwritten from .env usually
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

DEFAULT_CONFIG = default_config()

# Create a global GraphRunner instance
graph_runner = GraphRunner()


@app.get("/status")
async def status():
    return {"status": "ok"}


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    logger.info(
        "New WebSocket connection attempt"
    )  # Keep as info - important connection event
    await websocket.accept()
    logger.debug("WebSocket connection accepted")  # Changed from info to debug

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(
                f"Client message received: {data}"
            )  # Changed from info to debug

            try:
                client_payload = json.loads(data)
                task = client_payload.get("task", DEFAULT_CONFIG.get("task", ""))
                add_infos = client_payload.get("add_infos", "")
                logger.debug(f"Extracted task: {task}")  # Changed from info to debug
                logger.debug(
                    f"Extracted additional info: {add_infos}"
                )  # Changed from info to debug

                # Initialize graph runner at the start of each chat session
                config = DEFAULT_CONFIG.copy()
                agent_config = AgentConfig(
                    use_own_browser=config.get("use_own_browser", False),
                    keep_browser_open=config.get("keep_browser_open", True),
                    headless=config.get("headless", True),
                    disable_security=config.get("disable_security", False),
                    window_w=config.get("window_w", 1280),
                    window_h=config.get("window_h", 720),
                    task=task,  # Use the received task
                    add_infos=add_infos,  # Use received additional info
                    max_steps=config.get("max_steps", 10),
                    use_vision=config.get("use_vision", False),
                    max_actions_per_step=config.get("max_actions_per_step", 5),
                    tool_calling_method=config.get(
                        "tool_calling_method", "default_method"
                    ),
                    limit_num_image_per_llm_call=config.get(
                        "limit_num_image_per_llm_call", None
                    ),
                )

                logger.info(
                    "Initializing graph runner for new chat session"
                )  # Keep as info - important state change
                await graph_runner.initialize(agent_config)
                logger.debug(
                    "Graph runner initialized successfully"
                )  # Changed from info to debug

                async for update in graph_runner.execute(task):
                    logger.debug(
                        "Received update from graph runner"
                    )  # Changed from info to debug
                    logger.debug(
                        f"Update type: {type(update)}"
                    )  # Changed from info to debug
                    logger.debug(
                        f"Update content: {json.dumps(update, indent=2)}"
                    )  # Changed from info to debug

                    try:
                        # Skip None updates from graph runner
                        if update is None:
                            logger.debug("Skipping None update from graph runner")
                            continue

                        response_data = {
                            "html_content": update.get("html_content", ""),
                            "current_state": update.get("current_state") or {},
                            "action": update.get("action", []),
                        }

                        # Only send non-empty responses
                        if response_data["action"] or response_data["current_state"]:
                            logger.info(
                                f"Prepared response: {json.dumps(response_data, indent=2)}"
                            )
                            await websocket.send_text(json.dumps(response_data))
                            logger.info("Successfully sent response to client")

                    except Exception as serialize_error:
                        logger.error(
                            f"Serialization error: {str(serialize_error)}",
                            exc_info=True,
                        )
                        error_response = {
                            "error": "Response processing failed",
                            "details": str(serialize_error),
                        }
                        await websocket.send_text(json.dumps(error_response))

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse client message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_text(json.dumps({"error": error_msg}))
                continue

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


@app.websocket("/ws/stop")
async def stop_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection for stop requests")
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Stop request received: {data}")

            try:
                client_payload = json.loads(data)
                task = client_payload.get("task", "")

                # handle stop request
                if task == "stop":
                    logger.info("Received stop request")
                    response = (
                        await graph_runner.stop_agent()
                    )  # Changed from agent_runner to graph_runner
                    await websocket.send_text(json.dumps(response))
                    logger.info("Stop Response sent to UI")
                    return

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse client message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_text(json.dumps({"error": error_msg}))

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7788)
