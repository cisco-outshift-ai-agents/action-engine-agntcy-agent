import { create } from "zustand";

interface ChatStoreState {
  isThinking: boolean;
  setisThinking: (value: boolean) => void;
  isStopped: boolean;
  setIsStopped: (value: boolean) => void;
}

export const useChatStore = create<ChatStoreState>((set) => ({
  isThinking: false,
  setisThinking: (value) => set({ isThinking: value }),
  isStopped: false,
  setIsStopped: (value) => set({ isStopped: value }),
}));
