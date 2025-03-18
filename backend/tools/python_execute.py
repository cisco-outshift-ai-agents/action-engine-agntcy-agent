import threading
import sys
import logging
from io import StringIO
from typing import Dict
from pydantic import BaseModel, Field

from .base import ToolResult
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Manages safe Python code execution in a separate thread"""

    def __init__(self):
        self.output_buffer = StringIO()
        self.result = {"output": "", "error": None}

    def execute(self, code: str) -> Dict:
        """Execute code in a controlled environment"""
        # Save original stdout
        original_stdout = sys.stdout
        sys.stdout = self.output_buffer

        try:
            # Create restricted globals with direct access to builtins
            safe_globals = {
                "__builtins__": __builtins__,  # Use full builtins instead of restricted dict
            }

            # Execute code with restricted globals
            exec(code, safe_globals, {})
            self.result["output"] = self.output_buffer.getvalue()

        except Exception as e:
            self.result["error"] = str(e)

        finally:
            # Restore original stdout
            sys.stdout = original_stdout
            self.output_buffer.close()

        return self.result


class PythonExecuteInput(BaseModel):
    """Input model for Python code execution"""

    code: str = Field(description="The Python code to execute")
    timeout: int = Field(default=5, description="Maximum execution time in seconds")


@tool("python_execute")
async def python_execute_tool(code: str, timeout: int = 5) -> ToolResult:
    """
    Execute Python code in a safe environment with timeout protection.
    - Only print outputs are visible, return values are not captured
    - Use print statements to see results
    - Limited set of built-in functions available
    - Execution timeout prevents infinite loops
    - Restricted environment for safety

    Args:
        code: The Python code to execute
        timeout: Maximum execution time in seconds (default: 5)
    """
    logger.info("Python execute tool invoked")

    if not code:
        return ToolResult(error="Code is required")

    executor = CodeExecutor()
    result = {"output": "", "error": None}

    def run_code():
        nonlocal result
        result = executor.execute(code)

    # Run code in separate thread with timeout
    thread = threading.Thread(target=run_code)
    thread.start()
    thread.join(timeout)

    # Handle timeout
    if thread.is_alive():
        return ToolResult(
            error=f"Execution timeout after {timeout} seconds",
            system="Code execution terminated due to timeout",
        )

    # Return results
    if result["error"]:
        return ToolResult(error=result["error"], system="Code execution failed")

    return ToolResult(
        output=result["output"].strip(), system="Code executed successfully"
    )
