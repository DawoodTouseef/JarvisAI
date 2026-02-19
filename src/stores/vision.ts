import { create } from "zustand";

type VisionState = {
  screenActive: boolean;
  cameraEnabled: boolean;
  setScreenActive: (active: boolean) => void;
  setCameraEnabled: (enabled: boolean) => void;
};

export const useVisionStore = create<VisionState>((set) => ({
  screenActive: true,
  cameraEnabled: false,
  setScreenActive: (active) => set({ screenActive: active }),
  setCameraEnabled: (enabled) => set({ cameraEnabled: enabled })
}));
