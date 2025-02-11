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
            # create configuration by merging defaults with whatever value the client provides
            config = DEFAULT_CONFIG.copy()
            config.update({"task": task, "add_infos": add_infos})
            # log the config
            logger.info(f"Configuration: {config}")

            # process stream of updates from the agent

            try:
                async for update in run_with_stream(**config):
                    logger.info("Received update from agent")
                    logger.info(f"Update type: {type(update)}")

                    try:
                        # process updates if it's a list - this is the expected format

                        if isinstance(update, list):
                            html_content = update[0] if update else ""
                            brain_states = []
                            actions = []

                            for item in update:
                                if isinstance(item, list) and item:
                                    actions.extend(item)
                                elif hasattr(item, "prev_action_evaluation"):
                                    if hasattr(item, "model_dump"):
                                        brain_states.append(item.model_dump())
                                    elif hasattr(item, "dict"):
                                        brain_states.append(item.dict())

                            # construct response data
                            response_data = {
                                "html_content": html_content,
                                "current_state": (
                                    brain_states[-1] if brain_states else {}
                                ),
                                "action": [],
                            }

                            # Handle action serialization that could come in different formats (this fixes some serialization related errors in the logs)
                            for action in actions:
                                if hasattr(action, "model_dump"):
                                    response_data["action"].append(action.model_dump())
                                elif hasattr(action, "dict"):
                                    response_data["action"].append(action.dict())
                                elif isinstance(action, dict):
                                    response_data["action"].append(action)
                                else:
                                    response_data["action"].append(str(action))

                            # send response to client
                            json_string = json.dumps(response_data)
                            await websocket.send_text(json_string)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7788)
