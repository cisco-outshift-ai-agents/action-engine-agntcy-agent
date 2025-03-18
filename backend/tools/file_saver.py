import os
import logging
from typing import Union, Dict
from langchain_core.tools import tool
import aiofiles

from .base import ToolResult

logger = logging.getLogger(__name__)


@tool
async def file_saver_tool(
    content: str, file_path: str, mode: str = "w", mkdir: bool = True
) -> ToolResult:
    """Save content to a local file at a specified path.
    Use this tool when you need to save text, code, or generated content to a file on the local filesystem.
    The tool accepts content and a file path, and saves the content to that location.

    Args:
        content (str): The content to save to the file
        file_path (str): The path where the file should be saved, including filename and extension
        mode (str, optional): The file opening mode. Use 'w' for write or 'a' for append. Defaults to 'w'.
        mkdir (bool, optional): Create parent directories if they don't exist. Defaults to True.
    """
    logger.info(f"File saver tool invoked with file_path: {file_path}")

    try:
        if not file_path:
            return ToolResult(error="file_path is required")
        if not content:
            return ToolResult(error="content is required")

        if mkdir:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

        async with aiofiles.open(file_path, mode, encoding="utf-8") as file:
            await file.write(content)

        return ToolResult(
            output=f"Content successfully saved to {file_path}",
            system=f"File saved: {os.path.abspath(file_path)}",
        )

    except Exception as e:
        return ToolResult(
            error=f"Failed to save file: {str(e)}",
            system=f"Error while saving to {file_path}",
        )
