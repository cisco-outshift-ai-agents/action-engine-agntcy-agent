import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.graph.graph_runner import GraphRunner
from src.graph.environments.terminal import TerminalManager
from src.utils.default_config_settings import default_config

logging.basicConfig(
    level=logging.INFO,
    format="----%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = default_config()

terminal_manager = TerminalManager.get_instance()

graph_runner = GraphRunner(terminal_manager=terminal_manager)


class LLMConfig:
    provider: str
    model_name: str
    temperature: float
    base_url: str
    api_key: str


@dataclass
class AgentConfig:
    use_own_browser: bool
    keep_browser_open: bool
    headless: bool
    disable_security: bool
    window_w: int
    window_h: int
    task: str
    add_infos: str
    max_steps: int
    use_vision: bool
    max_actions_per_step: int
    tool_calling_method: str
    limit_num_image_per_llm_call: Optional[int]


@dataclass
class AgentResult:
    final_result: str
    errors: str
    model_actions: str
    model_thoughts: str
    latest_video: Optional[str]


# TODO: Add lifespan back
app = FastAPI(title="ActionEngine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def status():
    return {"status": "ok"}


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    logger.info(
        "New WebSocket connection attempt"
    )  # Keep as info - important connection event
    await websocket.accept()
    logger.debug("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Client message received: {data}")

            try:
                client_payload = json.loads(data)
                task = client_payload.get("task", DEFAULT_CONFIG.get("task", ""))
                add_infos = client_payload.get("add_infos", "")
                logger.debug(f"Extracted task: {task}")
                logger.debug(f"Extracted additional info: {add_infos}")

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

                logger.info("Initializing graph runner for new chat session")
                await graph_runner.initialize(agent_config)
                logger.debug("Graph runner initialized successfully")

                async for update in graph_runner.execute(task):
                    logger.debug("Received update from graph runner")
                    try:
                        # Skip None updates from graph runner
                        if update is None:
                            logger.debug("Skipping None update from graph runner")
                            continue

                        await websocket.send_text(json.dumps(update))

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
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/stop")
async def stop_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection for stop requests")
    await websocket.accept()

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
                    response = await graph_runner.stop_agent()
                    await websocket.send_text(json.dumps(response))
                    logger.info("Stop Response sent to UI")
                    return

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse client message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_text(json.dumps({"error": error_msg}))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/terminal")
async def terminal_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection for terminal commands")
    await websocket.accept()
    terminal_manager = TerminalManager.get_instance()

    # Create a new terminal for this WebSocket
    terminal_id = await terminal_manager.create_terminal()
    logger.info(f"Assigned terminal {terminal_id} to new WebSocket")

    try:
        # Start polling task for streaming output from this terminal
        async def poll_terminal():
            logger.info(f"Polling terminal output for terminal {terminal_id}")
            async for output in terminal_manager.poll_and_stream_output(terminal_id, 0):
                await websocket.send_text(json.dumps(output))

        poll_task = asyncio.create_task(poll_terminal())

        # Command input loop (from the same client)
        while True:
            data = await websocket.receive_text()
            client_payload = json.loads(data)

            if "command" in client_payload:
                command = client_payload["command"]
                logger.info(
                    f"Executing command from client on terminal {terminal_id}: {command}"
                )
                await terminal_manager.execute_command(terminal_id, command)

    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected for terminal {terminal_id}")
    finally:
        poll_task.cancel()
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7788)
