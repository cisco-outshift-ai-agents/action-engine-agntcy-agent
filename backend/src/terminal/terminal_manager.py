import os
import random
import shlex
import subprocess
import time
import logging
import asyncio
from typing import Dict, Any, Optional
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Registry

from src.terminal.terminal_views import TerminalCommandAction

logger = logging.getLogger(__name__)

import os
import random
import shlex
import subprocess
import time
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TerminalManager:
    """Manages terminal sessions and command execution using tmux"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TerminalManager, cls).__new__(cls)
            cls._instance.terminals = {}
            cls._instance.current_terminal_id = None
            logger.info("TerminalManager instance created")
        return cls._instance

    async def create_terminal(self) -> str:
        """Creates a new terminal session using tmux and returns its ID"""
        tmux_socket_path = os.environ.get("TMUX_SOCKET_PATH", "/root/.tmux/tmux-server")
        terminal_id = str(random.randint(1000, 9999))
        logger.info(f"Generated terminal ID: {terminal_id}")

        # Create the tmux session
        process = await asyncio.create_subprocess_exec(
            "tmux",
            "-S",
            tmux_socket_path,
            "new-session",
            "-d",
            "-s",
            terminal_id,
            "-c",
            str(os.path.expanduser("~")),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
            logger.error(f"Error creating terminal via subprocess: {error_msg}")
            raise Exception(f"Error creating terminal: {error_msg}")

        # Give tmux some time to fully initialize the session
        await asyncio.sleep(0.5)

        # Verify the session was created
        retries = 2
        while retries > 0:
            verify_session = await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "list-sessions",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            stdout, _ = await verify_session.communicate()
            if terminal_id in stdout.decode():
                break
            await asyncio.sleep(0.5)
            retries -= 1
        else:
            raise Exception(f"Failed to verify tmux session {terminal_id} creation")

        # Get the initial working directory
        working_dir = await self._get_working_directory(terminal_id, tmux_socket_path)

        # save the session details
        self.terminals[terminal_id] = {
            "session_name": terminal_id,
            "output": "",
            "working_directory": working_dir,
        }

        self.current_terminal_id = terminal_id

        print(f"Terminal {terminal_id} created with working directory: {working_dir}")
        return terminal_id

    async def _get_working_directory(
        self, terminal_id: str, tmux_socket_path: str
    ) -> str:
        """Get the current working directory of the terminal"""

        # Run pwd in the terminal and capture output
        start_marker = f"PWD_{random.randint(1000, 9999)}"
        end_marker = f"END_{random.randint(1000, 9999)}"

        await asyncio.create_subprocess_exec(
            "tmux",
            "-S",
            tmux_socket_path,
            "send-keys",
            "-t",
            terminal_id,
            f"echo {start_marker}",
            "C-m",
        )
        await asyncio.create_subprocess_exec(
            "tmux", "-S", tmux_socket_path, "send-keys", "-t", terminal_id, "pwd", "C-m"
        )
        await asyncio.create_subprocess_exec(
            "tmux",
            "-S",
            tmux_socket_path,
            "send-keys",
            "-t",
            terminal_id,
            f"echo {end_marker}",
            "C-m",
        )

        working_dir = os.path.expanduser("~")
        # Wait for output
        for _ in range(10):
            await asyncio.sleep(0.2)
            process = await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "capture-pane",
                "-p",
                "-t",
                terminal_id,
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            output = stdout.decode()

            if start_marker in output and end_marker in output:
                # Extract the working directory
                output_lines = (
                    output.split(start_marker, 1)[1]
                    .split(end_marker, 1)[0]
                    .strip()
                    .split("\n")
                )
                if len(output_lines) >= 2:
                    working_dir = output_lines[1].strip()
                break

        return working_dir

    async def execute_command(
        self, terminal_id: Optional[str], command: str
    ) -> tuple[str, bool]:
        """Execute a command in the specified terminal and return the output"""
        "Returns a tuple of (output, is_success)"
        try:
            tmux_socket_path = os.environ.get(
                "TMUX_SOCKET_PATH", "/root/.tmux/tmux-server"
            )
            session_name = None

            if terminal_id is None or terminal_id not in self.terminals:
                logger.warning(
                    f"Terminal {terminal_id} does not exist, creating a new one."
                )
                try:
                    terminal_id = await self.create_terminal()
                    session_name = self.terminals[terminal_id]["session_name"]
                except Exception as e:
                    error_msg = f"Error creating terminal: {str(e)}"
                    logger.error(error_msg)
                    return error_msg, False
            else:
                session_name = self.terminals[terminal_id]["session_name"]

            # Check if the terminal is busy
            if session_name:
                is_busy = await self._is_terminal_busy(session_name, tmux_socket_path)
                if is_busy:
                    logger.warning(
                        f"Terminal {terminal_id} is busy, creating a new terminal instead."
                    )
                    terminal_id = await self.create_terminal()
                    session_name = self.terminals[terminal_id]["session_name"]
            else:
                logger.error(
                    f"Terminal {terminal_id} does not have a valid session name."
                )
                return "Terminal does not have a valid session name", False

            # Use markers to identify the start and end of command output
            start_marker = f"===START_MARKER_{random.randint(10000, 99999)}==="
            end_marker = f"===END_MARKER_{random.randint(10000, 99999)}==="

            # Clear the terminal before executing the command
            await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "send-keys",
                "-t",
                session_name,
                "printf '\\033[2J\\033[H'",
                "C-m",
            )
            await asyncio.sleep(0.2)

            await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "send-keys",
                "-t",
                session_name,
                f"echo {start_marker}",
                "C-m",
            )
            await asyncio.sleep(0.1)
            await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "send-keys",
                "-t",
                session_name,
                command,
                "C-m",
            )
            await asyncio.sleep(0.5)

            await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "send-keys",
                "-t",
                session_name,
                f"echo {end_marker}",
                "C-m",
            )

            # Poll for output until end marker is found - up to 10 seconds
            for _ in range(20):
                await asyncio.sleep(0.5)
                capture_proc = await asyncio.create_subprocess_exec(
                    "tmux",
                    "-S",
                    tmux_socket_path,
                    "capture-pane",
                    "-p",
                    "-t",
                    session_name,
                    "-S",
                    "-5000",
                    stdout=asyncio.subprocess.PIPE,
                )
                stdout, _ = await capture_proc.communicate()
                output = stdout.decode() if stdout else ""

                if end_marker in output:
                    break
            else:
                logger.warning(f"Command execution timed out: {command}")
                return "Command execution timed out", False

            # Extract the command output between markers using get_terminal_output
            final_output = self.get_terminal_output(output, start_marker, end_marker)
            logger.info(
                f"Command executed successfully in terminal {terminal_id}: {final_output}"
            )

            if terminal_id in self.terminals:
                self.terminals[terminal_id]["output"] = final_output

                # Update the working directory
                self.terminals[terminal_id]["working_directory"] = (
                    await self._get_working_directory(terminal_id, tmux_socket_path)
                )
                self.current_terminal_id = terminal_id
            else:
                logger.warning(
                    f"Terminal {terminal_id} not found in terminals dictionary."
                )

                # Attempt recovery by adding it to the dictionary
                self.terminals[terminal_id] = {
                    "session_name": terminal_id,
                    "output": final_output,
                    "working_directory": await self._get_working_directory(
                        terminal_id, tmux_socket_path
                    ),
                }
                self.current_terminal_id = terminal_id

            return final_output, True

        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            logger.error(error_msg)

            working_dir = "~"
            if terminal_id in self.terminals:
                working_dir = self.terminals[terminal_id].get("working_directory", "~")
            return (
                f"Error executing command: {error_msg}\nCurrent directory: {working_dir}",
                False,
            )

    def get_terminal_output(
        self, output: str, start_marker: str, end_marker: str
    ) -> str:
        """Extract command output between markers and preserve original format"""
        logger.debug(f"Raw output: {output}")

        if start_marker not in output:
            logger.warning(f"Start marker '{start_marker}' not found in output")
            return "Command execution failed: Start marker not found"
        if end_marker not in output:
            logger.warning(f"End marker '{end_marker}' not found in output")
            return "Command execution failed: End marker not found"

        try:
            # Extract content between markers
            content_between_markers = output.split(start_marker, 1)[1].split(
                end_marker, 1
            )[0]
            logger.debug(f"Content between markers: {content_between_markers}")

            lines = content_between_markers.splitlines()
            cleaned_lines = []

            prompt_line_found = False

            for line in lines:
                # Skip markers and echo commands
                if (
                    start_marker in line
                    or end_marker in line
                    or line.strip().endswith("echo")
                ):
                    continue

                # Look for the prompt line (first occurrence only)
                if not prompt_line_found and "root@" in line and "#" in line:
                    prompt_parts = line.split("#", 1)
                    if len(prompt_parts) > 1 and prompt_parts[1].strip():
                        # This is a valid prompt with command
                        cleaned_lines.append(line)
                        prompt_line_found = True
                        continue

                # Skip empty prompt lines without commands
                if line.strip().startswith("root@") and "#" in line:
                    after_hash = line.split("#", 1)[1].strip()
                    if not after_hash:  # Empty command
                        continue

                # Add other content lines
                if line.strip():
                    cleaned_lines.append(line)

            # Join with newlines to preserve the original line-by-line format
            result = "\n".join(cleaned_lines).strip()
            logger.debug(f"Cleaned output: {result}")
            return result

        except Exception as e:
            logger.error(f"Error extracting output: {str(e)}")
            return f"Command execution failed: {str(e)}"

    async def get_terminal_output_history(self, terminal_id: str) -> str:
        """Get the current output of the terminal session"""
        if terminal_id not in self.terminals:
            raise ValueError(f"Terminal {terminal_id} does not exist")

        return self.terminals[terminal_id].get("output", "")

    async def get_terminal_state(self, terminal_id: str) -> Dict[str, Any]:
        """Get the current state of the terminal, ensuring it's still valid in tmux."""
        if terminal_id not in self.terminals:
            raise ValueError(
                f"Terminal {terminal_id} does not exist in TerminalManager."
            )

        if not await self.is_terminal_active(terminal_id):
            logger.warning(f"Terminal {terminal_id} is no longer active in tmux.")
            del self.terminals[terminal_id]
            raise ValueError(f"Terminal {terminal_id} no longer exists in tmux.")

        # Ensure working directory is up to date
        working_directory = self.terminals[terminal_id].get("working_directory", "")
        if not working_directory:
            tmux_socket_path = os.environ.get(
                "TMUX_SOCKET_PATH", "/root/.tmux/tmux-server"
            )
            working_directory = await self._get_working_directory(
                terminal_id, tmux_socket_path
            )

        return {
            "terminal_id": terminal_id,
            "output": self.terminals[terminal_id].get("output", ""),
            "working_directory": working_directory,
        }

    async def is_terminal_active(self, terminal_id: str) -> bool:
        """Check if a terminal session is active in tmux"""

        tmux_socket_path = os.environ.get("TMUX_SOCKET_PATH", "/root/.tmux/tmux-server")

        verify_session = await asyncio.create_subprocess_exec(
            "tmux",
            "-S",
            tmux_socket_path,
            "list-sessions",
            stdout=asyncio.subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        stdout, _ = await verify_session.communicate()
        active_sessions = stdout.decode()
        return terminal_id in active_sessions

    async def delete_terminal(self, terminal_id: Optional[str] = None) -> str:
        """Delete a terminal session or all terminal sessions"""
        if terminal_id:
            # Delete a particular terminal
            if terminal_id not in self.terminals:
                raise ValueError(f"Terminal {terminal_id} does not exist")

            session_name = self.terminals[terminal_id]["session_name"]
            # Kill the tmux session
            process = subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if process.returncode != 0:
                error_msg = (
                    process.stderr.decode("utf-8")
                    if process.stderr
                    else "Unknown error"
                )
                logger.error(f"Error deleting terminal {terminal_id}: {error_msg}")
                raise Exception(f"Error deleting terminal {terminal_id}: {error_msg}")

            del self.terminals[terminal_id]
            if self.current_terminal_id == terminal_id:
                self.current_terminal_id = None

            return f"Terminal {terminal_id} deleted"
        else:
            # Delete all terminals
            for tid, terminal in list(self.terminals.items()):
                session_name = terminal["session_name"]
                process = subprocess.run(
                    ["tmux", "kill-session", "-t", session_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            self.terminals = {}
            self.current_terminal_id = None
            return "All terminals deleted"

    async def get_current_terminal_id(self) -> Optional[str]:
        """Get the current terminal ID"""
        if not self.current_terminal_id:
            return None

        if not await self.is_terminal_active(self.current_terminal_id):
            logger.warning(
                f"Current terminal {self.current_terminal_id} is no longer active."
            )
            self.current_terminal_id = None
            return None

        return self.current_terminal_id

    async def list_terminals(self) -> Dict[str, Dict[str, Any]]:
        """List all active terminal sessions"""
        return self.terminals

    async def _is_pid_running(self, pid: str) -> bool:
        """Check if a process with the given PID is running"""
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False

    async def _is_terminal_busy(self, session_name: str, tmux_socket_path: str) -> bool:
        """Check if a tmux terminal is busy by checking active pane processes."""

        if not isinstance(session_name, str) or not session_name:
            raise ValueError("Invalid session name provided.")
        try:
            process = await asyncio.create_subprocess_exec(
                "tmux",
                "-S",
                tmux_socket_path,
                "list-panes",
                "-F",
                "#{pane_active} #{pane_pid}",
                "-t",
                session_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                error_msg = _.decode("utf-8") if _ else "Unknown error"
                logger.error(
                    f"Error checking terminal {session_name} status: {error_msg}"
                )
                return False

            output = stdout.decode().strip()

            for line in output.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0] == "1":
                    pid = parts[1]
                    if await self._is_pid_running(pid):
                        logger.info(
                            f"Terminal {session_name} is currently busy with process {pid}"
                        )
                        return True

            return False
        except Exception as e:
            logger.error(f"Error checking if terminal {session_name} is busy: {str(e)}")
            return False
