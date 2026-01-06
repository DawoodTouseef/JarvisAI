import {create } from "zustand";


type TranscriptionState = {
  isSpeaking: boolean;
  setText: (t: boolean) => void;
  clear: () => void;
};

export const useSpeakingStore = create<TranscriptionState>((set) => ({
  isSpeaking: false,
  setText: (t: boolean) => set({ isSpeaking: t }),
  clear: () => set({ isSpeaking: false }),
}));