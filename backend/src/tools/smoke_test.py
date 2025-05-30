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
import os
from pathlib import Path

from .browser_use import browser_use_tool
from .file_saver import file_saver_tool
from .google_search import google_search_tool
from .planning import planning_tool
from .python_execute import python_execute_tool
from .str_replace_editor import str_replace_editor_tool
from .terminal import terminal_tool
from .terminate import terminate_tool


async def test_browser():
    print("\n=== Testing Browser Tool ===")
    result = await browser_use_tool(
        action="go_to_url", params={"url": "https://www.example.com"}
    )
    print(f"Browser Result: {result}")


async def test_file_operations():
    print("\n=== Testing File Operations ===")
    test_dir = Path("/tmp/actionengine_test")
    test_file = test_dir / "test.txt"
    os.makedirs(test_dir, exist_ok=True)

    result = await file_saver_tool.ainvoke(
        {
            "input": {
                "content": "Hello World",
                "file_path": str(test_file),
                "mode": "w",
                "mkdir": True,
            }
        }
    )
    print(f"File Save Result: {result}")

    result = await str_replace_editor_tool.ainvoke(
        {"input": {"command": "view", "path": str(test_file)}}
    )
    print(f"File View Result: {result}")


async def test_google_search():
    print("\n=== Testing Google Search ===")
    result = await google_search_tool(query="LangGraph documentation", num_results=2)
    print(f"Search Result: {result}")


async def test_planning():
    print("\n=== Testing Planning Tool ===")
    result = await planning_tool.ainvoke(
        {
            "input": {
                "command": "create",
                "plan_id": "test_plan",
                "title": "Test Plan",
                "steps": ["Step 1", "Step 2"],
            }
        }
    )
    print(f"Planning Result: {result}")


async def test_python_execute():
    print("\n=== Testing Python Execute ===")
    code = """
print('Hello from Python')
x = [1, 2, 3]
print(f'Sum is {sum(x)}')
"""
    result = await python_execute_tool.ainvoke({"input": {"code": code}})
    print(f"Python Execute Result: {result}")


async def test_terminal():
    print("\n=== Testing Terminal Tool ===")
    result = await terminal_tool.ainvoke({"input": {"command": "pwd"}})
    print(f"Terminal Result: {result}")


async def test_terminate():
    print("\n=== Testing Terminate Tool ===")
    result = await terminate_tool.ainvoke(
        {"input": {"status": "success", "reason": "Smoke test complete"}}
    )
    print(f"Terminate Result: {result}")


async def main():
    """Run all smoke tests"""
    tests = [
        test_bash,
        test_terminal,
        test_python_execute,
        test_file_operations,
        test_planning,
        test_terminate,
    ]

    # Optional tests that may need configuration
    if os.getenv("TEST_BROWSER"):
        tests.append(test_browser)
    if os.getenv("TEST_GOOGLE"):
        tests.append(test_google_search)

    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"Error in {test.__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
