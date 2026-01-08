import { create } from "zustand";

type VideoState = {
  videostream: MediaStream | null,
  setVideoStream: (stream: MediaStream | null) => void,
  clear:()=> void
};

export const useVideoStore = create<VideoState>((set) => ({
  videostream: null,
  setVideoStream: (stream) => set({ videostream: stream }),
  clear: () => set({ videostream:null }),
}));
