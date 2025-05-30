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
import asyncio
import logging
from typing import Optional

from .base import ToolResult

# Constants for output management
MAX_RESPONSE_LEN: int = 16000
TRUNCATED_MESSAGE: str = (
    "<response clipped>"
    "<NOTE>To save on context only part of this response has been shown.</NOTE>"
)

logger = logging.getLogger(__name__)


def maybe_truncate(
    content: str, truncate_after: Optional[int] = MAX_RESPONSE_LEN
) -> str:
    """Truncate content if it exceeds specified length"""
    if not truncate_after or len(content) <= truncate_after:
        return content
    return content[:truncate_after] + TRUNCATED_MESSAGE


async def run_command(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: float = 120.0,
    truncate_after: Optional[int] = MAX_RESPONSE_LEN,
) -> ToolResult:
    """Run a shell command asynchronously with timeout and output management.

    Args:
        cmd: The shell command to execute
        cwd: The working directory to run the command in
        timeout: Maximum execution time in seconds
        truncate_after: Maximum length for output before truncation

    Returns:
        ToolResult containing command output or error
    """
    logger.info(f"Run command called with command: {cmd}")

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,  # Pass cwd to subprocess
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return ToolResult(
                output=maybe_truncate(stdout.decode(), truncate_after),
                error=(
                    maybe_truncate(stderr.decode(), truncate_after) if stderr else None
                ),
                system=f"Command completed with return code: {process.returncode}",
            )

        except asyncio.TimeoutError:
            try:
                process.kill()
                return ToolResult(
                    error=f"Command timed out after {timeout} seconds",
                    system="Process terminated due to timeout",
                )
            except ProcessLookupError:
                pass  # Process already finished

    except Exception as e:
        return ToolResult(error=str(e), system=f"Failed to execute command: {cmd}")


async def run_command_with_input(
    cmd: str,
    input_text: Optional[str] = None,
    timeout: float = 120.0,
    truncate_after: Optional[int] = MAX_RESPONSE_LEN,
) -> ToolResult:
    """Run a shell command that may require input.

    Args:
        cmd: The shell command to execute
        input_text: Optional text to send to process stdin
        timeout: Maximum execution time in seconds
        truncate_after: Maximum length for output before truncation

    Returns:
        ToolResult containing command output or error
    """
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE if input_text else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            if input_text and process.stdin:
                process.stdin.write(input_text.encode())
                await process.stdin.drain()
                process.stdin.close()

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return ToolResult(
                output=maybe_truncate(stdout.decode(), truncate_after),
                error=(
                    maybe_truncate(stderr.decode(), truncate_after) if stderr else None
                ),
                system=f"Command completed with return code: {process.returncode}",
            )

        except asyncio.TimeoutError:
            try:
                process.kill()
                return ToolResult(
                    error=f"Command timed out after {timeout} seconds",
                    system="Process terminated due to timeout",
                )
            except ProcessLookupError:
                pass

    except Exception as e:
        return ToolResult(error=str(e), system=f"Failed to execute command: {cmd}")
