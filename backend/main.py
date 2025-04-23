import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, APIRouter
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from dotenv import load_dotenv

# Initialize our core components
from src.graph.environments.terminal import TerminalManager
from src.utils.default_config_settings import default_config
from src.utils.stream_patch import stream_stateless_run_output
from src.lto.main import analyze_event_log, summarize_with_ai
from src.lto.storage import EventStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="----%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize workflow_srv first
from agent_workflow_server.agents.load import load_agents
from agent_workflow_server.main import app as WorkflowSrvApp
from agent_workflow_server.apis.agents import public_router as PublicAgentsApiRouter
from agent_workflow_server.apis.agents import router as AgentsApiRouter
from agent_workflow_server.apis.authentication import (
    setup_api_key_auth,
    authentication_with_api_key,
)
from agent_workflow_server.apis.stateless_runs import router as StatelessRunsApiRouter
from agent_workflow_server.services.queue import start_workers

from src.utils.queue_patch import (
    start_workers,
    stop_workers,
)

# Initialize components
DEFAULT_CONFIG = default_config()
event_storage = EventStorage()

# Load agents before using the app
load_agents()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting worker queue")
    workers = await start_workers(int(os.environ["NUM_WORKERS"]))
    yield
    logger.info("Stopping worker queue")
    await stop_workers()


app = FastAPI(lifespan=lifespan)

# Create router for our overrides
override_router = APIRouter()


# Add a stream endpoint since as of 4/23/2025, the streaming endpoint doesn't exist in WorkflowSrv
@override_router.get("/runs/{run_id}/stream")
async def stream_endpoint(run_id: str):
    return await stream_stateless_run_output(run_id)


# Include override router first so it takes precedence
app.include_router(override_router)


# Copy over routes from base app
for route in WorkflowSrvApp.routes:
    if route.path != "/runs/{run_id}/stream":
        app.router.routes.append(route)

# Copy over middleware
app.middleware = WorkflowSrvApp.middleware
app.user_middleware = WorkflowSrvApp.user_middleware
app.middleware_stack = WorkflowSrvApp.middleware_stack

# Initialize authentication
setup_api_key_auth(app)

app.get("/runs/{run_id}/stream")(stream_stateless_run_output)

# Add CORS middleware
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


@app.websocket("/ws/terminal")
async def terminal_endpoint(websocket: WebSocket):
    await websocket.accept()
    terminal_manager = TerminalManager.get_instance()
    terminal_id = await terminal_manager.create_terminal()
    logger.info(f"Assigned terminal {terminal_id} to new WebSocket connection")

    try:
        await websocket.send_text(
            json.dumps(
                {
                    "terminal_id": terminal_id,
                    "working_directory": "/root",
                    "summary": "",
                    "marker_id": 0,
                }
            )
        )
    except Exception as e:
        logger.error(f"Failed to send initial terminal ID: {e}", exc_info=True)
        return

    async def poll_terminal(tid):
        try:
            async for output in terminal_manager.poll_and_stream_output(tid, 0):
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(output))
                else:
                    break
        except Exception as e:
            logger.error(f"Polling error for terminal {tid}: {e}")

    poll_task = asyncio.create_task(poll_terminal(terminal_id))

    try:
        while True:
            data = await websocket.receive_text()
            client_payload = json.loads(data)

            if "command" in client_payload:
                command = client_payload["command"]
                logger.info(f"Executing command on terminal {terminal_id}: {command}")
                result, success = await terminal_manager.execute_command(
                    terminal_id, command
                )

                if not success:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "summary": f"Command execution failed: {result}",
                                "terminal_id": terminal_id,
                                "working_directory": terminal_manager.terminals[
                                    terminal_id
                                ]["working_directory"],
                                "error": True,
                            }
                        )
                    )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for terminal {terminal_id}")
    finally:
        if poll_task:
            poll_task.cancel()


@app.post("/api/event-log")
async def learning_through_observation_endpoint(request: Request):
    if not learning_enabled:
        return {"error": "Learning is not enabled"}

    try:
        event_data = await request.json()
        if not event_storage.get_current_session():
            session_id = event_storage.create_session()
            logger.info(f"Created new session: {session_id}")
        else:
            session_id = event_storage.get_current_session()

        event_data["session_id"] = session_id
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
            return {
                "error": "No active session",
                "message": "Please start a new session before analyzing events",
            }

        events = event_storage.get_session_events(session_id)
        if not events:
            return {
                "error": "No events found",
                "message": f"No events found for session {session_id}",
            }

        analyzed_result = await analyze_event_log(events)
        analyzed_result.session_id = session_id
        lto_response = await summarize_with_ai(analyzed_result)

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
async def clear_event_log():
    new_session = event_storage.create_session()
    return {"status": "success", "new_session_id": new_session}


if __name__ == "__main__":
    # Start worker queue
    n_workers = int(os.environ.get("NUM_WORKERS", 5))
    loop = asyncio.get_event_loop()
    loop.create_task(start_workers(n_workers))

    # Run server
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "7788")),
        loop="asyncio",
    )
