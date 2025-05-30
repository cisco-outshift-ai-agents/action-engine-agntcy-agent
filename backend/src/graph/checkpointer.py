# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
"""Custom checkpointer for handling environment objects."""

import logging
from typing import Any, Dict, Optional
from types import TracebackType
from contextlib import AbstractAsyncContextManager, AbstractContextManager, ExitStack
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    CheckpointTuple,
    SerializerProtocol,
)
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class EnvironmentAwareCheckpointer(
    BaseCheckpointSaver[str], AbstractContextManager, AbstractAsyncContextManager
):
    """Checkpointer that handles environment objects.

    This checkpointer wraps LangGraph's InMemorySaver but adds special handling for
    environment objects to prevent serialization issues.
    """

    def __init__(self, *, serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde)
        from src.graph.environments.store import environment_store

        self._env_store = environment_store
        self._memory_saver = InMemorySaver(serde=serde)  # Pass through serializer
        self.stack = ExitStack()

    def __enter__(self) -> "EnvironmentAwareCheckpointer":
        """Enter context manager."""
        return self.stack.__enter__()

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit context manager."""
        return self.stack.__exit__(exc_type, exc_value, traceback)

    async def __aenter__(self) -> "EnvironmentAwareCheckpointer":
        """Enter async context manager."""
        return self.stack.__enter__()

    async def __aexit__(
        self,
        __exc_type: Optional[type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit async context manager."""
        return self.stack.__exit__(__exc_type, __exc_value, __traceback)

    def _extract_envs(self, data: Any) -> Any:
        """Recursively extract environment objects from any data structure."""
        env_keys = [
            "browser",
            "browser_context",
            "dom_service",
            "terminal_manager",
            "planning_environment",
        ]

        if isinstance(data, dict):
            # Handle dictionaries recursively
            cleaned = {}
            envs = {}
            for k, v in data.items():
                if k in env_keys:
                    envs[k] = v
                else:
                    cleaned[k] = self._extract_envs(v)
            if envs:
                # If we found env objects, store them
                thread_id = data.get("thread_id")
                if thread_id:
                    self._env_store.set_envs(thread_id, envs)
            return cleaned
        elif isinstance(data, list):
            # Handle lists recursively
            return [self._extract_envs(item) for item in data]
        else:
            # Base case - return non-dict/list values as-is
            return data

    def _restore_envs(self, config_dict: Dict, thread_id: str):
        """Restore environment objects to config if available."""
        # Get environments from shared store
        thread_envs = self._env_store.get_envs(thread_id)
        if thread_envs:
            config_dict.update(thread_envs)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any],
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Store checkpoint while handling environment objects and channel values."""
        try:
            # Input validation
            if not isinstance(config, dict) or "configurable" not in config:
                raise ValueError("Config must be a dict with 'configurable' field")

            thread_id = config["configurable"].get("thread_id")
            if not thread_id:
                raise ValueError("Config must contain configurable.thread_id")

            logger.debug(f"Processing checkpoint for thread {thread_id}")

            # Create clean copies of all data structures
            c = dict(checkpoint) if checkpoint is not None else {}
            config_copy = dict(config)
            metadata_copy = dict(metadata) if metadata is not None else {}

            # Clean data structures
            c = self._extract_envs(c)
            cleaned_config = self._extract_envs(config_copy)
            cleaned_metadata = self._extract_envs(metadata_copy)

            # Ensure required LangGraph fields with defaults
            required_fields = {
                "pending_sends": [],
                "channel_values": {},
                "channel_versions": {},
            }
            for field, default in required_fields.items():
                if field not in c:
                    c[field] = default.copy()  # Use copy for mutable defaults

            logger.debug(f"Storing cleaned checkpoint with fields: {sorted(c.keys())}")
            return await self._memory_saver.aput(
                cleaned_config, c, cleaned_metadata, new_versions
            )

        except Exception as e:
            logger.error(f"Error storing checkpoint: {e}")
            logger.debug(f"Checkpoint structure: {checkpoint}")
            raise ValueError(f"Failed to store checkpoint: {str(e)}") from e

    async def aget_tuple(self, config: RunnableConfig):
        """Load checkpoint and restore environment objects if available."""
        try:
            # Input validation
            if not isinstance(config, dict) or "configurable" not in config:
                raise ValueError("Config must be a dict with 'configurable' field")

            thread_id = config["configurable"].get("thread_id")
            if not thread_id:
                raise ValueError("Config must contain configurable.thread_id")

            logger.debug(f"Loading checkpoint for thread {thread_id}")

            # Clean config before loading
            cleaned_config = self._extract_envs(dict(config))

            # Load checkpoint data
            result = await self._memory_saver.aget_tuple(cleaned_config)

            if not result:
                return result

            # Clean loaded data structures and make mutable copies
            cleaned_checkpoint = self._extract_envs(dict(result.checkpoint))
            cleaned_metadata = self._extract_envs(dict(result.metadata))

            # Ensure required LangGraph fields with defaults
            required_fields = {
                "pending_sends": [],
                "channel_values": {},
                "channel_versions": {},
            }
            for field, default in required_fields.items():
                if field not in cleaned_checkpoint:
                    cleaned_checkpoint[field] = default.copy()

            # Restore environment objects if needed
            if "configurable" in cleaned_checkpoint:
                logger.debug("Restoring environment objects")
                self._restore_envs(cleaned_checkpoint["configurable"], thread_id)

            logger.debug(
                f"Restored checkpoint with fields: {sorted(cleaned_checkpoint.keys())}"
            )
            # Create new checkpoint tuple with cleaned data
            # Note: channel_versions comes from checkpoint dict, not the tuple
            return CheckpointTuple(
                config=cleaned_config,  # Required
                checkpoint=cleaned_checkpoint,  # Required
                metadata=cleaned_metadata,  # Required
                parent_config=None,  # Optional
                pending_writes=None,  # Optional
            )

        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            logger.debug(f"Config: {config}")
            raise ValueError(f"Failed to load checkpoint: {str(e)}") from e

    # Implement other required methods by delegating to memory_saver
    async def alist(self, *args, **kwargs):
        """List checkpoints by delegating to memory saver."""
        return self._memory_saver.alist(*args, **kwargs)

    async def aput_writes(self, *args, **kwargs):
        """Store writes by delegating to memory saver."""
        return await self._memory_saver.aput_writes(*args, **kwargs)

    def get_next_version(self, current: Optional[str], channel: Any) -> str:
        """Get next version for a channel, delegating to memory saver."""
        return self._memory_saver.get_next_version(current, channel)
