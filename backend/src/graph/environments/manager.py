"""Thread-aware environment managers for GraphRunner."""

import logging
from typing import Dict, Optional
from uuid import uuid4

from src.graph.environments.terminal import TerminalManager
from src.graph.environments.browser import BrowserEnvironment
from src.graph.environments.planning import PlanningEnvironment

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages thread-specific environments for GraphRunner."""

    def __init__(self):
        self._environments: Dict[str, "ThreadEnvironments"] = {}

    async def get_or_create(self, thread_id: str) -> "ThreadEnvironments":
        """Get or create thread-specific environments."""
        if thread_id not in self._environments:
            terminal_manager = (
                TerminalManager.get_instance()
            )  # TODO: Make thread-specific
            browser_manager = BrowserEnvironment()
            planning_manager = PlanningEnvironment()

            self._environments[thread_id] = ThreadEnvironments(
                terminal_manager=terminal_manager,
                browser_manager=browser_manager,
                planning_manager=planning_manager,
                thread_id=thread_id,
            )

        return self._environments[thread_id]

    async def cleanup(self, thread_id: str) -> None:
        """Clean up environments for a specific thread."""
        if thread_id in self._environments:
            await self._environments[thread_id].cleanup()
            del self._environments[thread_id]


class ThreadEnvironments:
    """Container for thread-specific environment instances."""

    def __init__(
        self,
        terminal_manager: TerminalManager,
        browser_manager: BrowserEnvironment,
        planning_manager: PlanningEnvironment,
        thread_id: str,
    ):
        self.thread_id = thread_id
        self.terminal_manager = terminal_manager
        self.browser_manager = browser_manager
        self.planning_manager = planning_manager
        self._initialized = False

    async def initialize(self, config: Optional[dict] = None) -> None:
        """Initialize all environments for this thread."""
        if self._initialized:
            return

        config = config or {}

        # Initialize browser with thread-specific config
        await self.browser_manager.initialize(
            window_w=config.get("window_w", 1280), window_h=config.get("window_h", 720)
        )

        # Initialize terminal (if needed)
        # The terminal manager is already a singleton, but we could make it thread-aware

        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up all environments for this thread."""
        try:
            await self.browser_manager.cleanup()
            await self.terminal_manager.delete_terminal()  # Could be made thread-specific
            self._initialized = False
        except Exception as e:
            logger.error(
                f"Error cleaning up environments for thread {self.thread_id}: {e}"
            )


# Global environment manager instance
environment_manager = EnvironmentManager()
