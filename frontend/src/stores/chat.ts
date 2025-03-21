import { create } from "zustand";
import { GraphData } from "@/pages/session/types";

interface ChatStoreState {
  isThinking: boolean;
  isStopped: boolean;
  plan: NonNullable<GraphData["plan"]> | null;
}

interface ChatStoreActions {
  setisThinking: (value: boolean) => void;
  setIsStopped: (value: boolean) => void;
  setPlan: (value: NonNullable<GraphData["plan"]> | null) => void;
}

export const useChatStore = create<ChatStoreState & ChatStoreActions>(
  (set) => ({
    isThinking: false,
    setisThinking: (value) => set({ isThinking: value }),

    isStopped: false,
    setIsStopped: (value) => set({ isStopped: value }),

    plan: null,
    setPlan: (value) => set({ plan: value }),
  })
);
