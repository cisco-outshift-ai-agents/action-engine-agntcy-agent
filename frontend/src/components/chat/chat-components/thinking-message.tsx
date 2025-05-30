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
import { cn } from "@/utils";
import CiscoAIAssistantLogo from "@/components/chat/chat-assets/cisco-ai-assistant.png";
import ChatMessageText from "./chat-message-text";

interface ThinkingMessageProps {
  summary?: string | null;
  thought?: string | null;
}

const ThinkingMessage: React.FC<ThinkingMessageProps> = ({
  summary,
  thought,
}) => {
  if (!summary && !thought) return null;

  return (
    <div className={cn("text-l text-[#f7f7f7]")}>
      <div className="py-2 rounded-xl bg-[#373C42]">
        <div className="flex items-start px-4">
          <img
            src={CiscoAIAssistantLogo}
            alt="outshift-logo"
            width={24}
            className="mr-3 mt-0.5"
          />
          <div className="flex flex-col">
            <ChatMessageText
              content={summary}
              thought={thought}
              role="assistant"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThinkingMessage;
