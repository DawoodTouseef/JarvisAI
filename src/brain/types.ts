export enum AssistantState {
    IDLE = "IDLE",
    LISTENING = "LISTENING",
    THINKING = "THINKING",
    SPEAKING = "SPEAKING",
    INTERRUPTED = "INTERRUPTED",
    PAUSED = "PAUSED",
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED",
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED",
}

export interface BrainEvent {
    type: string;
    payload?: any;
    timestamp: number;
}

export interface ClarificationPayload {
    question_text: string;
}

export interface PermissionPayload {
    command_summary: string;
    exact_operation: string;
    risk_level: string;
    request_id?: string;
    source?: "system" | "autonomous";
    query?: string;
}

export interface BrainStateData {
    clarification?: ClarificationPayload | null;
    permission?: PermissionPayload | null;
    taskId?: string | null;
}

export type VADStatus = "speech_start" | "speech_end" | "silence";

export interface BrainConfig {
    bargeInEnabled: boolean;
    silenceTimeoutMs: number;
}
