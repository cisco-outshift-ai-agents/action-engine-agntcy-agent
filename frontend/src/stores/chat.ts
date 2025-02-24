import { create } from "zustand";

interface ChatStoreState {
  isThinking: boolean;
  setisThinking: (value: boolean) => void;
}

export const useChatStore = create<ChatStoreState>((set) => ({
  isThinking: false,
  setisThinking: (value) => set({ isThinking: value }),
}));
