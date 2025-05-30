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
# SPDX-License-Identifier: Apache-2.0
*/
import Markdown from "@/components/chat/markdown";
import { TodoFixAny } from "@/types";
import {
  MessageCircleMore,
  MousePointerClick,
  TextCursorIcon,
  Terminal,
} from "lucide-react";
import { ReactNode } from "react";

const ChatMessageText: React.FC<ChatMessageTextProps> = ({
  content,
  isThinking,
  role,
  thought,
  actions,
}) => {
  return (
    <div className="flex gap-2 flex-col">
      {thought && (
        <div className="flex flex-col gap-1 text-xs text-gray-400 mb-2">
          <span>
            <MessageCircleMore className="inline w-4 h-4 mr-2" />
            {thought}
          </span>
        </div>
      )}
      <div className="flex items-center">
        <div className="overflow-hidden font-light w-full">
          {content && role === "user" && (
            <p className="font-normal text-base tracking-normal text-[#F7F7F7] whitespace-pre-wrap break-words leading-[22px]">
              {content}
            </p>
          )}

          {content && role === "assistant" && (
            <Markdown>{content as TodoFixAny}</Markdown>
          )}

          {!content && (
            <span className="text-muted-foreground text-sm">
              No response provided
            </span>
          )}
        </div>
        {isThinking && <span>...</span>}
      </div>
      {actions && actions.length > 0 && (
        <div className="flex flex-col gap-1 text-xs text-gray-400 mt-2">
          {actions.map((action, index) => (
            <span key={index}>
              {action.toLowerCase().includes("click") && (
                <MousePointerClick className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action.toLowerCase().includes("input text") && (
                <TextCursorIcon className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action.toLowerCase().includes("execute terminal") && (
                <Terminal className="inline w-4 h-4 mr-2 flex-shrink-0" />
              )}
              {action}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

interface ChatMessageTextProps {
  content: ReactNode | undefined | null;
  errors?: string[] | undefined | null;
  warnings?: string[] | undefined | null;
  isThinking?: boolean | undefined | null;
  thought?: string | undefined | null;
  actions?: string[] | undefined | null;
  role: "user" | "assistant";
}

export default ChatMessageText;
