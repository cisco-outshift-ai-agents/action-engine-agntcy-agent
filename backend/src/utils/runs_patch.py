"""Patched version of workflow server's runs service with improved stream handling."""

import asyncio
import logging
from typing import AsyncIterator, Optional

from agent_workflow_server.services.message import Message
from agent_workflow_server.services.runs import Runs as BaseRuns, RUNS_QUEUE
from agent_workflow_server.storage.storage import DB

logger = logging.getLogger(__name__)


class PatchedRunsService(BaseRuns):
    """Extends workflow server's Runs service with improved streaming."""

    class Stream:
        """Patched stream implementation with better timeout handling."""

        @staticmethod
        async def publish(run_id: str, message: Message) -> None:
            await BaseRuns.Stream.publish(run_id, message)

        @staticmethod
        async def subscribe(run_id: str) -> asyncio.Queue:
            return await BaseRuns.Stream.subscribe(run_id)

        @staticmethod
        async def join(run_id: str) -> AsyncIterator[Message]:
            """Join a run's stream with improved timeout handling.

            Waits for first message without timeout to allow for initialization,
            then uses timeouts only for subsequent messages.
            """
            queue = await PatchedRunsService.Stream.subscribe(run_id)

            # Check run exists
            run = DB.get_run(run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")
            if run["status"] != "pending" and queue.empty():
                return

            try:
                # Wait for first message without timeout
                first_message = await queue.get()
                yield first_message
                if first_message.type == "control" and first_message.data == "done":
                    return

                # After first message, use timeout for subsequent messages
                while True:
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=10)
                        yield message
                        if message.type == "control" and message.data == "done":
                            break
                    except TimeoutError:
                        # Check if run is still active
                        run = DB.get_run(run_id)
                        if run and run["status"] != "pending":
                            logger.debug(
                                f"Run {run_id} completed with status {run['status']}"
                            )
                            break  # Run is complete
                        logger.debug(
                            f"No message received for {run_id} in last 10s, continuing to wait"
                        )
                        continue  # Keep waiting for more messages

            except Exception as error:
                logger.error(f"Error processing messages for run {run_id}: {error}")
                raise  # Re-raise the error to be handled by caller

    @staticmethod
    async def stream_events(run_id: str) -> AsyncIterator[Message]:
        """Override stream_events to use our patched Stream implementation."""
        async for message in PatchedRunsService.Stream.join(run_id):
            yield message

    # Inherit all other methods from base Runs service
    @staticmethod
    async def put(run_create: "ApiRunCreate") -> "ApiRun":
        """Create a new run and add it to the queue."""
        new_run = BaseRuns._make_run(run_create)
        run_info = {
            "run_id": new_run["run_id"],
            "queued_at": datetime.now(),
            "attempts": 0,
        }
        DB.create_run(new_run)
        DB.create_run_info(run_info)

        logger.debug(f"Adding run {new_run['run_id']} to queue")
        await RUNS_QUEUE.put(new_run["run_id"])
        return BaseRuns._to_api_model(new_run)

    # Inherit other methods from base Runs service
    get = BaseRuns.get
    delete = BaseRuns.delete
    get_all = BaseRuns.get_all
    search_for_runs = BaseRuns.search_for_runs
    resume = BaseRuns.resume
    set_status = BaseRuns.set_status
    wait = BaseRuns.wait
    wait_for_output = BaseRuns.wait_for_output


def patch_runs_service():
    """Apply the patch to the Runs service with improved stream handling."""
    import agent_workflow_server.services.runs

    logger.info("Patching workflow server Runs service with improved stream handling")
    agent_workflow_server.services.runs.Runs = PatchedRunsService


# Apply the patch when this module is imported
patch_runs_service()
