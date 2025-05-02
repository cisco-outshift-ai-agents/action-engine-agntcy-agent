"""Patched version of workflow server's queue service with fixed worker initialization."""

import asyncio
import logging
from typing import List

from agent_workflow_server.services.queue import (
    worker as base_worker,
    log_run,
    MAX_RETRY_ATTEMPTS,
)

logger = logging.getLogger(__name__)


async def patched_start_workers(n_workers: int) -> List[asyncio.Task]:
    """Start worker tasks without blocking.

    Creates worker tasks but doesn't await their completion since they run indefinitely.
    Returns the task objects so they can be cancelled if needed.
    """
    logger.info(f"Starting {n_workers} workers")
    return [asyncio.create_task(base_worker(i + 1)) for i in range(n_workers)]


def patch_queue_service():
    """Apply the patch to fix worker initialization."""
    import agent_workflow_server.services.queue

    logger.info(
        "Patching workflow server queue service with fixed worker initialization"
    )
    agent_workflow_server.services.queue.start_workers = patched_start_workers
