import { create } from "zustand";

export type AgentState =
  | "idle"
  | "listening"
  | "thinking"
  | "calling_tool"
  | "executing"
  | "waiting_for_permission"
  | "speaking"
  | "error";

export type AgentActivity = {
  id: string;
  timestamp: string;
  agent?: string;
  message: string;
  tool?: string;
  level?: "info" | "warning" | "error";
};

type AgentSystemState = {
  state: AgentState;
  activeAgent?: string | null;
  toolName?: string | null;
  errorMessage?: string | null;
  activity: AgentActivity[];
  setState: (state: AgentState, agent?: string | null) => void;
  setActiveAgent: (agent?: string | null) => void;
  setToolName: (tool?: string | null) => void;
  addActivity: (activity: Omit<AgentActivity, "id">) => void;
  setError: (message?: string | null) => void;
  clearActivity: () => void;
};

const MAX_ACTIVITY = 30;

export const useAgentSystemStore = create<AgentSystemState>((set) => ({
  state: "idle",
  activeAgent: null,
  toolName: null,
  errorMessage: null,
  activity: [],
  setState: (state, agent) => set((prev) => ({
    state,
    activeAgent: agent ?? prev.activeAgent
  })),
  setActiveAgent: (agent) => set(() => ({ activeAgent: agent ?? null })),
  setToolName: (tool) => set(() => ({ toolName: tool ?? null })),
  addActivity: (activity) => set((prev) => {
    const next = [
      {
        id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
        ...activity
      },
      ...prev.activity
    ];
    return { activity: next.slice(0, MAX_ACTIVITY) };
  }),
  setError: (message) => set(() => ({ errorMessage: message ?? null })),
  clearActivity: () => set(() => ({ activity: [] }))
}));
