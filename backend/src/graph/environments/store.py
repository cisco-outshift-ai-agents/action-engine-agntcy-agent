"""Shared environment storage for thread environments."""

from typing import Any, Dict, Optional


class ThreadEnvironmentStore:
    """Store for managing thread-specific environments.

    Acts as a single source of truth for environment object references across the app.
    """

    _instance = None
    _thread_envs: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_envs(cls, thread_id: str) -> Dict[str, Any]:
        """Get environment objects for a thread."""
        return cls._thread_envs.get(thread_id, {})

    @classmethod
    def set_envs(cls, thread_id: str, envs: Dict[str, Any]):
        """Store environment objects for a thread."""
        cls._thread_envs[thread_id] = envs

    @classmethod
    def remove_envs(cls, thread_id: str):
        """Remove environment objects for a thread."""
        cls._thread_envs.pop(thread_id, None)


environment_store = ThreadEnvironmentStore()
