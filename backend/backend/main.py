import asyncio
import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_runner import AgentConfig, AgentRunner, LLMConfig
from src.terminal.terminal_manager import TerminalManager
from src.utils.default_config_settings import default_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = default_config()

agent_runner = AgentRunner()
active_terminal_websockets = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    terminal_manager = TerminalManager.get_instance()

    config = DEFAULT_CONFIG.copy()
    config["keep_browser_open"] = True

    agent_config = AgentConfig(
        use_own_browser=config.get("use_own_browser", False),
        keep_browser_open=config.get("keep_browser_open", True),
        headless=config.get("headless", True),
        disable_security=config.get("disable_security", False),
        window_w=config.get("window_w", 1280),
        window_h=config.get("window_h", 720),
        task=config.get("task", ""),
        add_infos=config.get("add_infos", ""),
        max_steps=config.get("max_steps", 10),
        use_vision=config.get("use_vision", False),
        max_actions_per_step=config.get("max_actions_per_step", 5),
        tool_calling_method=config.get("tool_calling_method", "default_method"),
        limit_num_image_per_llm_call=config.get("limit_num_image_per_llm_call", None),
    )
    llm_config = LLMConfig(
        provider=config.get("llm_provider", "openai"),
        model_name=config.get("llm_model_name", "gpt-3.5-turbo"),
        temperature=config.get("llm_temperature", 0.7),
        base_url=config.get("llm_base_url", ""),
        api_key=config.get("llm_api_key", ""),
    )
    await agent_runner.initialize_browser(agent_config)
    logger.info("Browser pre-initialized at server startup.")

    yield


app = FastAPI(title="ActionEngine API", lifespan=lifespan)

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
    logger.info("New WebSocket connection attempt")
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Client message received: {data}")
            client_payload = json.loads(data)
            task = client_payload.get("task", DEFAULT_CONFIG.get("task", ""))
            add_infos = client_payload.get("add_infos", "")

            config = DEFAULT_CONFIG.copy()
            config.update({"task": task, "add_infos": add_infos})

            agent_config = AgentConfig(
                use_own_browser=config.get("use_own_browser", False),
                keep_browser_open=config.get("keep_browser_open", True),
                headless=config.get("headless", True),
                disable_security=config.get("disable_security", False),
                window_w=config.get("window_w", 1280),
                window_h=config.get("window_h", 720),
                task=config.get("task", ""),
                add_infos=config.get("add_infos", ""),
                max_steps=config.get("max_steps", 10),
                use_vision=config.get("use_vision", False),
                max_actions_per_step=config.get("max_actions_per_step", 5),
                tool_calling_method=config.get("tool_calling_method", "default_method"),
                limit_num_image_per_llm_call=config.get(
                    "limit_num_image_per_llm_call", None
                ),
            )
            llm_config = LLMConfig(
                provider=config.get("llm_provider", "openai"),
                model_name=config.get("llm_model_name", "gpt-3.5-turbo"),
                temperature=config.get("llm_temperature", 0.7),
                base_url=config.get("llm_base_url", ""),
                api_key=config.get("llm_api_key", ""),
            )

            async for update in agent_runner.stream_agent_updates(
                llm_config, agent_config
            ):
                response_data = {
                    "html_content": update.get("html_content", ""),
                    "current_state": update.get("current_state") or {},
                    "action": update.get("action", []),
                }

                await websocket.send_text(json.dumps(response_data))

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
            client_payload = json.loads(data)
            if client_payload.get("task") == "stop":
                response = await agent_runner.stop_agent()
                await websocket.send_text(json.dumps(response))
                return
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
