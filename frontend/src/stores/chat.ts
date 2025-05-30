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
import { create } from "zustand";
import { GraphData } from "@/pages/session/types";
import { ChatMessageProps } from "@/components/chat/chat-components/chat-message";

interface ChatStoreState {
  isThinking: boolean;
  isStopped: boolean;
  plan: NonNullable<GraphData["plan"]> | null;
  messages: ChatMessageProps[];
}

interface ChatStoreActions {
  setisThinking: (value: boolean) => void;
  setIsStopped: (value: boolean) => void;
  setPlan: (value: NonNullable<GraphData["plan"]> | null) => void;
  addMessage: (msg: ChatMessageProps) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStoreState & ChatStoreActions>(
  (set) => ({
    isThinking: false,
    setisThinking: (value) => set({ isThinking: value }),

    isStopped: false,
    setIsStopped: (value) => set({ isStopped: value }),

    plan: null,
    setPlan: (value) => set({ plan: value }),

    messages: [],
    addMessage: (msg) => {
      console.log("💾 Adding message to store:", msg);

      set((state) => ({
        messages: [...state.messages, msg],
      }));
    },
    clearMessages: () => set({ messages: [] }),
  })
);
