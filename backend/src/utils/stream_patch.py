"""Patched version of stateless runs API with streaming support."""

import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import HTTPException, Path
from fastapi.responses import StreamingResponse
from typing_extensions import Annotated
from pydantic import SecretStr

from agent_workflow_server.services.runs import Runs
from agent_workflow_server.generated.models.run_output_stream import RunOutputStream
from agent_workflow_server.services.stream import stream_run

logger = logging.getLogger(__name__)


def format_sse_event(data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


def format_sse_error(error: Exception | str) -> str:
    """Format error as Server-Sent Event."""
    error_msg = str(error) if isinstance(error, Exception) else error
    return format_sse_event({"error": error_msg})


def format_sse_message(message_type: str, event: str | None, data: Any) -> str:
    """Format message as Server-Sent Event."""
    return format_sse_event({"type": message_type, "event": event, "data": data})


async def generate_sse_events(run_id: str) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events from run stream."""
    logger.info(f"Starting SSE stream for run {run_id}")

    try:
        # Get run as Pydantic model
        run = Runs.get(run_id)
        if not run:
            logger.error(f"Run {run_id} not found")
            yield format_sse_error(f"Run {run_id} not found")
            return

        logger.info(f"Got run data: agent_id={run.agent_id}, thread_id={run.thread_id}")

        # Convert config to dict format LangGraph expects
        config = {}
        if run.creation.config:
            config = run.creation.config.model_dump()
            # Ensure required fields exist
            config.setdefault("configurable", {})
            config.setdefault("tags", [])
            config.setdefault("recursion_limit", 25)
            # Skip logging config since it contains secrets

        # Convert to dict format that stream_run expects
        run_dict = {
            "run_id": run.run_id,
            "thread_id": run.thread_id,
            "agent_id": run.agent_id,
            "input": run.creation.input,
            "config": config,
            "metadata": run.creation.metadata,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }
        logger.debug(f"Created run dict with keys: {list(run_dict.keys())}")

        # Pass through messages directly as SSE events
        try:
            logger.info("Starting message stream")
            async for message in stream_run(run_dict):
                logger.debug(f"Got message: type={message.type}, event={message.event}")
                yield format_sse_message(
                    message_type=message.type, event=message.event, data=message.data
                )
        except Exception as e:
            logger.error(f"Error streaming run {run_id}: {e}", exc_info=True)
            yield format_sse_error(e)

    except Exception as e:
        logger.error(f"Error setting up stream for run {run_id}: {e}", exc_info=True)
        yield format_sse_error(e)


async def stream_stateless_run_output(
    run_id: Annotated[str, Path(description="The ID of the run.")],
) -> RunOutputStream:
    """Stream output from a run in Server-Sent Events format.

    Implements GET /runs/{run_id}/stream endpoint.
    """
    logger.info(f"Stream endpoint called for run {run_id}")
    try:
        return StreamingResponse(
            generate_sse_events(run_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        logger.error(f"Failed to setup streaming for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to setup streaming: {str(e)}"
        )
