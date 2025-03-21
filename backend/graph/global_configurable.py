import logging
from typing import Any, Dict, Optional

from browser_use.dom.service import DomService
from langchain_core.language_models import BaseChatModel
from langgraph.graph import Graph

from graph.environments.terminal import TerminalManager
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)


class GlobalConfigurableContext:
    """Global context for sharing resources across the application"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalConfigurableContext, cls).__new__(cls)
            cls._instance._browser = None
            cls._instance._browser_context = None
            cls._instance._dom_service = None
            cls._instance._terminal_manager = None
            cls._instance._llm = None
            cls._instance._graph = None
        return cls._instance

    @property
    def browser(self) -> Optional[CustomBrowser]:
        return self._browser

    @browser.setter
    def browser(self, value: CustomBrowser):
        self._browser = value

    @property
    def browser_context(self) -> Optional[CustomBrowserContext]:
        return self._browser_context

    @browser_context.setter
    def browser_context(self, value: CustomBrowserContext):
        self._browser_context = value

    @property
    def dom_service(self) -> Optional[DomService]:
        return self._dom_service

    @dom_service.setter
    def dom_service(self, value: DomService):
        self._dom_service = value

    @property
    def terminal_manager(self) -> Optional[TerminalManager]:
        return self._terminal_manager

    @terminal_manager.setter
    def terminal_manager(self, value: TerminalManager):
        self._terminal_manager = value

    @property
    def llm(self) -> Optional[BaseChatModel]:
        return self._llm

    @llm.setter
    def llm(self, value: BaseChatModel):
        self._llm = value

    @property
    def graph(self) -> Optional[Graph]:
        return self._graph

    @graph.setter
    def graph(self, value: Graph):
        self._graph = value


# Global singleton instance
context = GlobalConfigurableContext()


# Convenience functions for getting resources
def get_browser() -> Optional[CustomBrowser]:
    return context.browser


def get_browser_context() -> Optional[CustomBrowserContext]:
    return context.browser_context


def get_dom_service() -> Optional[DomService]:
    return context.dom_service


def get_terminal_manager() -> Optional[TerminalManager]:
    return context.terminal_manager


def get_llm() -> Optional[BaseChatModel]:
    return context.llm


def get_graph() -> Optional[Graph]:
    return context.graph
