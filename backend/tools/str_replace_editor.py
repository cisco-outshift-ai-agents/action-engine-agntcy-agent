import logging
import asyncio

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from .base import ToolResult
from langchain_core.tools import tool

# Constants
SNIPPET_LINES: int = 4
MAX_RESPONSE_LEN: int = 16000
TRUNCATED_MESSAGE: str = (
    "<response clipped><NOTE>To save on context only part of this file has been shown."
    "You should retry this tool after you have searched inside the file with `grep -n` "
    "in order to find the line numbers of what you are looking for.</NOTE>"
)

logger = logging.getLogger(__name__)


class FileHistoryManager:
    """Manages file history with proper locking and cleanup"""

    def __init__(self):
        self._history: Dict[Path, List[str]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._max_history_per_file = 100  # Prevent unbounded growth

    async def add_history(self, path: Path, content: str) -> None:
        """Add file content to history with bounds checking"""
        async with self._lock:
            history = self._history[path]
            history.append(content)
            # Maintain bounded history
            if len(history) > self._max_history_per_file:
                history.pop(0)

    async def get_last_version(self, path: Path) -> Optional[str]:
        """Get last version of file content"""
        async with self._lock:
            history = self._history[path]
            return history.pop() if history else None

    def cleanup(self, path: Optional[Path] = None) -> None:
        """Clean up history for a path or all paths"""
        if path:
            self._history.pop(path, None)
        else:
            self._history.clear()


# Create singleton instance
_file_manager = FileHistoryManager()


def maybe_truncate(
    content: str, truncate_after: Optional[int] = MAX_RESPONSE_LEN
) -> str:
    """Truncate content if it exceeds length"""
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


def _make_output(
    file_content: str,
    file_descriptor: str,
    init_line: int = 1,
    expand_tabs: bool = True,
) -> str:
    """Format file content for display"""
    file_content = maybe_truncate(file_content)
    if expand_tabs:
        file_content = file_content.expandtabs()
    file_content = "\n".join(
        [
            f"{i + init_line:6}\t{line}"
            for i, line in enumerate(file_content.split("\n"))
        ]
    )
    return (
        f"Here's the result of running `cat -n` on {file_descriptor}:\n"
        + file_content
        + "\n"
    )


class EditorCommand(str, Enum):
    """Available editor commands"""

    VIEW = "view"
    CREATE = "create"
    STR_REPLACE = "str_replace"
    INSERT = "insert"
    UNDO_EDIT = "undo_edit"


class EditorInput(BaseModel):
    """Input model for file editor actions"""

    command: EditorCommand = Field(description="The editor command to execute")
    path: str = Field(description="Absolute path to file or directory")
    file_text: Optional[str] = Field(None, description="Content for create command")
    old_str: Optional[str] = Field(None, description="Exact string to replace")
    new_str: Optional[str] = Field(None, description="New string to insert")
    insert_line: Optional[int] = Field(None, description="Line number for insertion")
    view_range: Optional[List[int]] = Field(
        None, description="Optional line range to view [start, end]"
    )


@tool
async def str_replace_editor_tool(
    command: EditorCommand,
    path: str,
    file_text: Optional[str] = None,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    insert_line: Optional[int] = None,
    view_range: Optional[List[int]] = None,
) -> ToolResult:
    """
    Custom editing tool for viewing, creating and editing files.
    - State is persistent across command calls
    - Commands available:
      - view: shows file content with line numbers
      - create: adds new files (won't overwrite)
      - str_replace: updates content with exact match
      - insert: adds new content at specified line
      - undo_edit: reverts last change

    Args:
        command: The editor command to execute
        path: Absolute path to file or directory
        file_text: Content for create command
        old_str: Exact string to replace
        new_str: New string to insert
        insert_line: Line number for insertion
        view_range: Optional line range to view [start, end]
    """
    logger.info(f"Str replace editor tool invoked with command: {command}")

    try:
        # Convert path to absolute Path object
        path_obj = Path(path)
        if not path_obj.is_absolute():
            # Convert relative path to absolute using current working directory
            path_obj = Path.cwd() / path_obj
            path_obj = path_obj.resolve()  # Resolve any .. or . in path

        # Validate path
        if path_obj.exists() and command == EditorCommand.CREATE:
            return ToolResult(error=f"Cannot create: {path_obj} already exists")

        if not path_obj.exists() and command != EditorCommand.CREATE:
            return ToolResult(error=f"Path does not exist: {path_obj}")

        if path_obj.is_dir() and command != EditorCommand.VIEW:
            return ToolResult(
                error=f"Path {path_obj} is a directory, only view command allowed"
            )

        # Execute commands
        if command == EditorCommand.VIEW:
            if path_obj.is_dir():
                # List directory contents
                content = "\n".join(
                    str(p) for p in path_obj.glob("**/*") if not str(p).startswith(".")
                )
                return ToolResult(output=f"Contents of {path_obj}:\n{content}")

            # Read file with optional range
            content = path_obj.read_text()
            if view_range:
                start, end = view_range
                lines = content.split("\n")
                if not (0 < start <= len(lines) and start <= end):
                    return ToolResult(
                        error=f"Invalid range: {start}-{end} for {len(lines)} lines"
                    )
                content = "\n".join(lines[start - 1 : end])

            return ToolResult(output=_make_output(content, str(path_obj)))

        elif command == EditorCommand.CREATE:
            if not file_text:
                return ToolResult(error="file_text required for create command")

            path_obj.write_text(file_text)
            await _file_manager.add_history(path_obj, file_text)

            return ToolResult(
                output=f"Created file: {path_obj}\n"
                + _make_output(file_text, str(path_obj))
            )

        elif command == EditorCommand.STR_REPLACE:
            if not old_str:
                return ToolResult(error="old_str required for str_replace command")

            content = path_obj.read_text().expandtabs()
            old_str_expanded = old_str.expandtabs()
            new_str_expanded = new_str.expandtabs() if new_str else ""

            # Verify unique match
            count = content.count(old_str_expanded)
            if count == 0:
                return ToolResult(error=f"String not found: {old_str_expanded}")
            if count > 1:
                return ToolResult(
                    error=f"Multiple matches ({count}) for: {old_str_expanded}"
                )

            # Make replacement
            new_content = content.replace(old_str_expanded, new_str_expanded)
            path_obj.write_text(new_content)
            await _file_manager.add_history(path_obj, content)

            # Show snippet around change
            line_num = content.split(old_str_expanded)[0].count("\n")
            start = max(0, line_num - SNIPPET_LINES)
            end = line_num + SNIPPET_LINES + new_str_expanded.count("\n")
            snippet = "\n".join(new_content.split("\n")[start : end + 1])

            return ToolResult(
                output=f"Updated file: {path_obj}\n"
                + _make_output(snippet, f"snippet of {path_obj}", start + 1)
            )

        elif command == EditorCommand.INSERT:
            if insert_line is None or new_str is None:
                return ToolResult(
                    error="insert_line and new_str required for insert command"
                )

            content = path_obj.read_text()
            lines = content.split("\n")
            line_num = insert_line

            if not (0 <= line_num <= len(lines)):
                return ToolResult(error=f"Invalid line number: {line_num}")

            # Insert content
            new_lines = lines[:line_num] + new_str.split("\n") + lines[line_num:]
            new_content = "\n".join(new_lines)
            path_obj.write_text(new_content)
            await _file_manager.add_history(path_obj, content)

            # Show snippet
            start = max(0, line_num - SNIPPET_LINES)
            end = line_num + SNIPPET_LINES
            snippet = "\n".join(new_lines[start:end])

            return ToolResult(
                output=f"Updated file: {path_obj}\n"
                + _make_output(snippet, f"snippet of {path_obj}", start + 1)
            )

        elif command == EditorCommand.UNDO_EDIT:
            content = await _file_manager.get_last_version(path_obj)
            if not content:
                return ToolResult(error=f"No history for {path_obj}")

            path_obj.write_text(content)
            return ToolResult(
                output=f"Reverted last change to {path_obj}\n"
                + _make_output(content, str(path_obj))
            )

    except Exception as e:
        return ToolResult(error=str(e))
