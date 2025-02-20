import { create } from "zustand";

interface ChatStoreState {
  isProcessing: boolean;
  setIsProcessing: (value: boolean) => void;
}

export const useChatStore = create<ChatStoreState>((set) => ({
  isProcessing: false,
  setIsProcessing: (value) => set({ isProcessing: value }),
}));
