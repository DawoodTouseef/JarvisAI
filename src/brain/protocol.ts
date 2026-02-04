export type RequestId = string;
export type TaskId = string;

// ----- Client -> Server Messages -----

export interface ClientMessageMap {
    "agent_task_submit": {
        type: "agent_task_submit";
        request_id: RequestId;
        payload: {
            name: string;
            query: string;
            auth_token?: string;
            base_url?: string;
        };
        metadata?: {
            task_type?: string;
            source?: string;
        };
    };

    "agent_task_cancel": {
        type: "agent_task_cancel";
        request_id: RequestId;
        payload: {
            task_id: TaskId;
        };
    };

    "agent_task_status": {
        type: "agent_task_status";
        request_id: RequestId;
        payload: {
            task_id?: TaskId;
            status?: string;
        };
    };

    "agent_clarification_response": {
        type: "agent_clarification_response";
        request_id: RequestId;
        payload: {
            task_id: TaskId;
            response: string;
        };
    };
}

export type ClientMessage = ClientMessageMap[keyof ClientMessageMap];

// ----- Server -> Client Messages -----

export interface ServerMessageMap {
    "agent_task_submitted": {
        type: "agent_task_submitted";
        request_id: RequestId;
        success: boolean;
        task_id?: TaskId;
        error?: string;
    };

    "agent_response": {
        type: "agent_response";
        task_id: TaskId;
        status: "completed" | "failed" | "running";
        result?: any;
        error?: string;
        use_tts?: boolean;
        timestamp: string;
    };

    "agent_clarification_request": {
        type: "agent_clarification_request";
        task_id: TaskId;
        question: string;
        use_tts?: boolean;
        isListening?: boolean;
        timestamp: string;
    };

    "agent_clarification_ack": {
        type: "agent_clarification_ack";
        task_id: TaskId;
        success: boolean;
    };

    "agent_error": {
        type: "agent_error" | "agent_task_submit_error" | "agent_task_cancel_error" | "clarification_error";
        success: false;
        error: string;
        timestamp: string;
    };
}

export type ServerMessage = ServerMessageMap[keyof ServerMessageMap];

// ----- Type Guards -----

export function isServerMessage(msg: any): msg is ServerMessage {
    return msg && typeof msg.type === "string";
}

export function isBinaryMessage(msg: any): msg is ArrayBuffer {
    return msg instanceof ArrayBuffer || msg instanceof Blob;
}
