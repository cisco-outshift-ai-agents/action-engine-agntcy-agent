from __future__ import annotations

import logging
from typing import List, Optional, Type

from browser_use.agent.message_manager.service import MessageManager
from browser_use.agent.message_manager.views import MessageHistory
from browser_use.agent.prompts import AgentMessagePrompt, SystemPrompt
from browser_use.agent.views import ActionModel, ActionResult, AgentStepInfo
from browser_use.browser.views import BrowserState
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from src.terminal.Terminal_message_manager import TerminalMessageManager

from .custom_prompts import CustomAgentMessagePrompt

logger = logging.getLogger(__name__)


class CustomMassageManager(MessageManager):
    def __init__(
        self,
        llm: BaseChatModel,
        task: str,
        action_descriptions: str,
        system_prompt_class: Type[SystemPrompt],
        agent_prompt_class: Type[AgentMessagePrompt],
        max_input_tokens: int = 128000,
        estimated_characters_per_token: int = 3,
        # https://ai.google.dev/gemini-api/docs/vision?lang=rest#tokens_4
        # 1920x1080 image generates 6 tiles of 768x720
        # 1 tile = 258 tokens
        # 6 tiles = 1548 tokens
        image_tokens: int = 1548,
        include_attributes: list[str] = [],
        max_error_length: int = 400,
        max_actions_per_step: int = 10,
        message_context: Optional[str] = None,
    ):
        super().__init__(
            llm=llm,
            task=task,
            action_descriptions=action_descriptions,
            system_prompt_class=system_prompt_class,
            max_input_tokens=max_input_tokens,
            estimated_characters_per_token=estimated_characters_per_token,
            image_tokens=image_tokens,
            include_attributes=include_attributes,
            max_error_length=max_error_length,
            max_actions_per_step=max_actions_per_step,
            message_context=message_context,
        )
        self.agent_prompt_class = agent_prompt_class
        # Custom: Move Task info to state_message
        self.history = MessageHistory()
        self._add_message_with_tokens(self.system_prompt)

        if self.message_context:
            context_message = HumanMessage(content=self.message_context)
            self._add_message_with_tokens(context_message)

    def cut_messages(self):
        """Get current message list, potentially trimmed to max tokens"""
        diff = self.history.total_tokens - self.max_input_tokens
        min_message_len = 2 if self.message_context is not None else 1

        while diff > 0 and len(self.history.messages) > min_message_len:
            self.history.remove_message(
                min_message_len
            )  # alway remove the oldest message
            diff = self.history.total_tokens - self.max_input_tokens

    def add_state_message(
        self,
        state: BrowserState,
        actions: Optional[List[ActionModel]] = None,
        result: Optional[List[ActionResult]] = None,
        step_info: Optional[AgentStepInfo] = None,
        terminal_message_manager: Optional[TerminalMessageManager] = None,
    ) -> None:
        """Add browser state as human message"""
        # otherwise add state message and result to next message (which will not stay in memory)
        prompt = self.agent_prompt_class(
            state,
            actions,
            result,
            include_attributes=self.include_attributes,  # type: ignore
            max_error_length=self.max_error_length,
            step_info=step_info,
        )

        if terminal_message_manager:
            setattr(prompt, "terminal_message_manager", terminal_message_manager)
        state_message = prompt.get_user_message()
        self._add_message_with_tokens(state_message)

    def _count_text_tokens(self, text: str) -> int:
        if isinstance(self.llm, (ChatOpenAI, ChatAnthropic)):
            try:
                tokens = self.llm.get_num_tokens(text)
            except Exception:
                tokens = (
                    len(text) // self.estimated_characters_per_token
                )  # Rough estimate if no tokenizer available
        else:
            tokens = (
                len(text) // self.estimated_characters_per_token
            )  # Rough estimate if no tokenizer available
        return tokens

    def _remove_state_message_by_index(self, remove_ind=-1) -> None:
        """Remove last state message from history"""
        i = len(self.history.messages) - 1
        remove_cnt = 0
        while i >= 0:
            if isinstance(self.history.messages[i].message, HumanMessage):
                remove_cnt += 1
            if remove_cnt == abs(remove_ind):
                self.history.remove_message(i)
                break
            i -= 1
