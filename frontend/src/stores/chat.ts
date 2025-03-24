import { create } from "zustand";
import { GraphData } from "@/pages/session/types";
import { ChatMessageProps } from "@/components/newsroom/newsroom-components/chat-message";

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
      set((state) => ({
        messages: [...state.messages, msg],
      }));
    },
    clearMessages: () => set({ messages: [] }),
  })
);
