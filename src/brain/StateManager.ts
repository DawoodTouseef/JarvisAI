import { AssistantState, BrainStateData } from "./types";
import { create } from "zustand";

interface StateStore {
    currentState: AssistantState;
    data: BrainStateData;
    setState: (state: AssistantState, data?: BrainStateData) => void;
    setData: (data: Partial<BrainStateData>) => void;
}

export const useBrainState = create<StateStore>((set) => ({
    currentState: AssistantState.IDLE,
    data: {},
    setState: (state, data) => {
        set((prev) => ({
            currentState: state,
            data: data ? { ...prev.data, ...data } : prev.data
        }));
    },
    setData: (data) => {
        set((prev) => ({
            data: { ...prev.data, ...data }
        }));
    }
}));

export class StateManager {

    public getCurrentState(): AssistantState {
        return useBrainState.getState().currentState;
    }

    public getData(): BrainStateData {
        return useBrainState.getState().data;
    }

    public transitionTo(newState: AssistantState, data?: BrainStateData): boolean {
        useBrainState.getState().setState(newState, data);
        return true;
    }

    public updateData(data: Partial<BrainStateData>) {
        useBrainState.getState().setData(data);
    }
}
