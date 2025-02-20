import { create } from "zustand";

interface ChatState {
  isProcessing: boolean;
  setIsProcessing: (value: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isProcessing: false,
  setIsProcessing: (value) => set({ isProcessing: value }),
}));
