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
# SPDX-License-Identifier: Apache-2.0
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
