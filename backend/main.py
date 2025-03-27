import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware

from src.graph.environments.terminal import TerminalManager
from src.graph.graph_runner import GraphRunner
from src.utils.default_config_settings import default_config
from src.lto.main import analyze_event_log, summarize_with_ai
from src.lto.storage import EventStorage
from src.models import AgentConfig

logging.basicConfig(
    level=logging.INFO,
    format="----%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = default_config()

terminal_manager = TerminalManager.get_instance()

graph_runner = GraphRunner(terminal_manager=terminal_manager)

event_storage = EventStorage()

# TODO: Add lifespan back
app = FastAPI(title="ActionEngine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

learning_enabled = False


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

                if client_payload.get("task") == "stop":
                    logger.info("Received stop request")
                    response = await graph_runner.stop_agent()
                    await websocket.send_text(json.dumps(response))
                    logger.info("Stop Response sent to UI")
                    return

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


# Gathers information from the VNC server browser and stores it in event_log
@app.post("/api/event-log")
async def learning_through_observation_endpoint(request: Request):
    logger.info("New request for learning observation")

    if not learning_enabled:
        return {"error": "Learning is not enabled"}

    try:
        event_data = await request.json()
        # Create a session if it doesn't exist
        if not event_storage.get_current_session():
            session_id = event_storage.create_session()
            logger.info(f"Created new session: {session_id}")
        else:
            session_id = event_storage.get_current_session()

        # Add session_id to event data
        event_data["session_id"] = session_id

        # Store raw event data
        file_path = event_storage.store_event(event_data)
        logger.info(f"Stored event in {file_path}")

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Event stored successfully",
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/event-log/analyze")
async def analyze_event_log_endpoint():
    session_id = event_storage.current_session
    logger.info(f"New request for analyzing event log for session {session_id}")

    try:
        if not session_id:
            logger.warning("No active session found")
            return {
                "error": "No active session",
                "message": "Please start a new session before analyzing events",
            }

        # Retrieve events for the session
        events = event_storage.get_session_events(session_id)

        if not events:
            logger.info(f"No events found for session {session_id}")
            return {
                "error": "No events found",
                "message": f"No events found for session {session_id}",
            }

        analyzed_result = await analyze_event_log(events)
        analyzed_result.session_id = session_id

        # Get summary and plan
        lto_response = await summarize_with_ai(analyzed_result)
        logger.info("Generated plan and summary")

        # Return just the plan data matching PlanZod schema
        return {
            "plan": (
                lto_response.plan.dict()
                if lto_response.plan
                else {"plan_id": None, "steps": []}
            )
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/learning")
async def toggle_learning_mode(request: Request):
    global learning_enabled
    data = await request.json()
    learning_enabled = data["learning_enabled"]
    logger.info(f"Learning mode set to: {learning_enabled}")
    return {"status": "success", "learning_enabled": learning_enabled}


@app.get("/api/learning")
async def get_learning_mode():
    return {"learning_enabled": learning_enabled}


@app.delete("/api/event-log")
async def clear_event_log(session_id: str = None):
    new_session = event_storage.create_session()
    return {"status": "success", "new_session_id": new_session}


@app.websocket("/ws/get-events")
async def get_events_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection for getting events")
    await websocket.accept()
    logger.info("WebSocket connection accepted for getting events")

    try:
        while True:
            session_id = event_storage.get_current_session()
            if session_id:
                events = event_storage.get_session_events(session_id)
                # Convert events to dict before JSON serialization
                events_json = [event.model_dump() for event in events]
                await websocket.send_text(json.dumps(events_json))
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for getting events")
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {str(e)}", exc_info=True)
    finally:
        logger.info("Closing WebSocket connection for getting events")
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7788)
