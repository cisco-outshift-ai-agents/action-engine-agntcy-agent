import { create } from "zustand";

interface ChatStoreState {
  isThinking: boolean;
  isStopped: boolean;
  plan: string;
}

interface ChatStoreActions {
  setisThinking: (value: boolean) => void;
  setIsStopped: (value: boolean) => void;
  setPlan: (value: string) => void;
}

export const useChatStore = create<ChatStoreState & ChatStoreActions>(
  (set) => ({
    isThinking: false,
    setisThinking: (value) => set({ isThinking: value }),

    isStopped: false,
    setIsStopped: (value) => set({ isStopped: value }),

    plan: "",
    setPlan: (value) => set({ plan: value }),
  })
);
