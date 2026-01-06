import {create} from "zustand";

type Transcription = {
  text:string,
  updated:Date
}
type TranscriptionState = {
  text: Array<Transcription>;
  setText: (t: Array<Transcription>) => void;
  clear: () => void;
};

export const useTranscriptionStore = create<TranscriptionState>((set) => ({
  text: [],
  setText: (t: Array<Transcription>) => set({ text: [{
    text:t,
    updated: new Date()
  }] }),
  clear: () => set({ text: [] }),
}));
