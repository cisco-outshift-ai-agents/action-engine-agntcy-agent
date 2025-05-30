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
import asyncio
import logging

from googlesearch import search
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .base import ToolResult

logger = logging.getLogger(__name__)


class GoogleSearchInput(BaseModel):
    """Input parameters for Google search"""

    query: str = Field(description="The search query to submit to Google")
    num_results: int = Field(
        default=10, description="The number of search results to return"
    )
    lang: str = Field(
        default="en",
        description="Language code for search results (e.g., 'en' for English)",
    )
    safe: bool = Field(default=True, description="Enable safe search filtering")


@tool("google_search")
async def google_search_tool(
    query: str, num_results: int = 10, lang: str = "en", safe: bool = True
) -> ToolResult:
    """
    Perform a Google search and return a list of relevant links.
    Use this tool when you need to:
    - Find information on the web
    - Get up-to-date data
    - Research specific topics
    - Find relevant websites

    Args:
        query: The search query to submit to Google
        num_results: Number of search results to return (default: 10)
        lang: Language code for search results (default: "en")
        safe: Enable safe search filtering (default: True)
    """
    logger.info(f"Google search tool invoked with query: {query}")

    try:
        # Run search in thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        links = await loop.run_in_executor(
            None,
            lambda: list(search(query, num_results=num_results, lang=lang, safe=safe)),
        )

        if not links:
            return ToolResult(output=[], system="No results found for query")

        return ToolResult(
            output=links, system=f"Found {len(links)} results for query: {query}"
        )

    except Exception as e:
        return ToolResult(
            error=f"Search failed: {str(e)}",
            system=f"Error performing search for query: {query}",
        )
