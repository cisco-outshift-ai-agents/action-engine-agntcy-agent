/*
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
*/
import React, { useRef, useState } from "react";
import TextareaAutosize from "react-textarea-autosize";
import { Button } from "./ui/button";
import { SendHorizontal, StopCircle } from "lucide-react";
import { cn } from "@/utils";

import ChatMessage from "./chat/chat-components/chat-message";
import CiscoAIAssistantLoader from "@/components/chat/chat-assets/thinking.gif";
import PlanRenderer from "./plan-renderer";

import { useChatStore } from "@/stores/chat";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useChatScroll } from "@/hooks/use-chat-scroll";

const ChatSection: React.FC<ChatSectionProps> = () => {
  const [input, setInput] = useState("");
  const bottomOfChatRef = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);

  const { messages, plan } = useChatStore();
  const {
    sendMessage: sendChatMessage,
    handleHitlConfirmation,
    stopTask,
    isThinking,
    isStopped,
  } = useChatStream();

  // Setup auto-scrolling
  useChatScroll(bottomOfChatRef, chatContainerRef, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isThinking) return;
    await sendChatMessage(input);
    setInput("");
  };

  return (
    <div className="h-[95%] rounded-lg  bg-[#32363c] w-full px-2 py-4 flex flex-col border-white/10 border">
      <PlanRenderer plan={plan} />
      <div
        className="flex-1 overflow-y-auto px-2 pt-2 pb-3"
        ref={chatContainerRef}
      >
        <div className="flex flex-col gap-4 space-y-reverse">
          {messages.map((message, index) => (
            <div key={index}>
              <ChatMessage
                {...message}
                onHitlConfirmation={handleHitlConfirmation}
              />
            </div>
          ))}
          {isThinking && (
            <div className="flex items-start px-2 py-2">
              <img
                src={CiscoAIAssistantLoader}
                alt="outshift-logo"
                width={36}
                className="mr-3 "
              />
            </div>
          )}
        </div>
        <div ref={bottomOfChatRef}></div>
      </div>
      <div className="px-4 pt-2 pb-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className={cn(
            "max-w-3xl mx-auto bg-[#373c42] border-2 border-[#7E868F] pr-3 pt-2 pl-5 pb-2 rounded-lg",
            "group focus-within:border-[#649EF5] flex items-center"
          )}
        >
          <TextareaAutosize
            tabIndex={1}
            minRows={1}
            maxRows={8}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What do you want ActionEngine to do?"
            className={cn(
              "w-full bg-transparent text-white font-normal text-base leading-[22px] placeholder:text-[#889099] placeholder:text-sm focus:ring-0 focus:border-0 focus:outline-none resize-none"
            )}
            wrap="hard"
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) return;
              if (e.key === "Enter" && !isThinking) {
                e.preventDefault();
                handleSend();
              } else if (e.key === "Enter" && isThinking) {
                e.preventDefault();
              }
            }}
          />
          <Button
            type="button"
            variant="ghost"
            className="p-1 hover:opacity-80"
            onClick={isThinking ? stopTask : handleSend}
            disabled={isThinking && isStopped}
          >
            {isThinking ? (
              <StopCircle className="w-[18.83px] h-[20.73px] text-[#649EF5]" />
            ) : (
              <SendHorizontal className="w-[18.83px] h-[20.73px] text-[#649EF5]" />
            )}
          </Button>
        </form>
        <div className="text-center mt-2 text-xs text-[#D0D4D9]">
          Assistant can make mistakes. Verify responses.
        </div>
      </div>
    </div>
  );
};

interface ChatSectionProps {
  className?: string;
  onTerminalUpdate?: (
    content: string,
    isTerminal: boolean,
    hasEmptyThought: boolean,
    isDone: boolean,
    terminalId: string,
    workingDirectory: string
  ) => void;
}

export default ChatSection;
