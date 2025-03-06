import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_runner import AgentConfig, AgentRunner, LLMConfig
from src.utils.default_config_settings import default_config

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

DEFAULT_CONFIG = default_config()

# Create a global AgentRunner instance
agent_runner = AgentRunner()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = DEFAULT_CONFIG.copy()
    # Persist the browser instance on startup.
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

            try:
                client_payload = json.loads(data)
                task = client_payload.get("task", DEFAULT_CONFIG.get("task", ""))
                add_infos = client_payload.get("add_infos", "")
                logger.info(f"Extracted task: {task}")
                logger.info(f"Extracted additional info: {add_infos}")
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse client message: {str(e)}"
                logger.error(error_msg)
                await websocket.send_text(json.dumps({"error": error_msg}))
                continue

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

            try:
                async for update in agent_runner.stream_agent_updates(
                    llm_config, agent_config
                ):
                    logger.info("Received update from agent")
                    logger.info(f"Update type: {type(update)}")
                    logger.info(f"Update content: {json.dumps(update, indent=2)}")

                    try:

                        response_data = {
                            "html_content": update.get("html_content", ""),
                            "current_state": update.get("current_state") or {},
                            "action": update.get("action", []),
                        }

                        if update.get("action") and len(update["action"]) > 0:
                            action = update["action"][0]

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

            except Exception as stream_error:
                logger.error(
                    f"Stream processing error: {str(stream_error)}", exc_info=True
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "error": "Stream processing failed",
                            "details": str(stream_error),
                        }
                    )
                )

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
                task = client_payload.get("task",  "")
               

                #handle stop request
                if task == "stop":
                    logger.info("Received stop request")
                    response =  await agent_runner.stop_agent()
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7788)
