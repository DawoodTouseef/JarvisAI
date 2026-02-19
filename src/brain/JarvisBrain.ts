import { StateManager, useBrainState } from "./StateManager";
import { TurnManager } from "./TurnManager";
import { AssistantState, BrainConfig, BrainStateData } from "./types";
import { ttsEngine } from "../lib/tts/TtsManager";
import { useAgentSystemStore } from "@/stores/agentSystem";

const DEFAULT_CONFIG: BrainConfig = {
    bargeInEnabled: true,
    silenceTimeoutMs: 2000,
};

export class JarvisBrain {
    private static instance: JarvisBrain;

    private stateManager: StateManager;
    private turnManager: TurnManager;
    private config: BrainConfig;
    private currentTaskId: string | null = null;
    private shouldListenAfterTts: boolean = false;

    private constructor(config: BrainConfig = DEFAULT_CONFIG) {
        this.config = config;
        this.stateManager = new StateManager();
        this.turnManager = new TurnManager(config);
    }

    public static getInstance(): JarvisBrain {
        if (!JarvisBrain.instance) {
            JarvisBrain.instance = new JarvisBrain();
        }
        return JarvisBrain.instance;
    }

    // ----- Public API Methods -----

    public handleWakeWordDetected() {
        // Only wake if not already processing something critical, or allow override?
        // For now, always wake.
        this.stateManager.transitionTo(AssistantState.LISTENING);
    }

    public async initialize() {
        const { AgentCommunication } = await import("../lib/client_websocket");

        ttsEngine.addCallbacks({
            onStart: () => {
                this.stateManager.transitionTo(AssistantState.SPEAKING);
            },
            onEnd: () => {
                const currentState = this.stateManager.getCurrentState();
                if (this.shouldListenAfterTts && (currentState === AssistantState.CLARIFICATION_REQUIRED || currentState === AssistantState.PAUSED)) {
                    this.shouldListenAfterTts = false;
                    this.stateManager.transitionTo(AssistantState.LISTENING);
                    return;
                }
                if (currentState === AssistantState.SPEAKING) {
                    this.stateManager.transitionTo(AssistantState.IDLE);
                }
            },
            onError: (err) => {
                console.error("[TTS] Error:", err);
            }
        });

        AgentCommunication.onMessage((msg) => {
            try {
                const data = JSON.parse(msg);
                const { type, task_id, payload } = data;

                // Sync current task ID if provided
                if (task_id) {
                    this.currentTaskId = task_id;
                    this.stateManager.updateData({ taskId: task_id });
                }

                switch (type) {
                    case "agent_state": {
                        const { setState } = useAgentSystemStore.getState();
                        if (payload?.state) {
                            setState(payload.state, payload.agent);
                        }
                        break;
                    }
                    case "active_agent": {
                        const { setActiveAgent } = useAgentSystemStore.getState();
                        setActiveAgent(payload?.agent);
                        break;
                    }
                    case "tool_name": {
                        const { setToolName, addActivity } = useAgentSystemStore.getState();
                        setToolName(payload?.tool_name);
                        if (payload?.tool_name || payload?.agent) {
                            addActivity({
                                agent: payload?.agent,
                                message: `Calling tool ${payload?.tool_name || ""}`.trim(),
                                timestamp: new Date().toISOString()
                            });
                        }
                        break;
                    }
                    case "agent_activity": {
                        const { addActivity } = useAgentSystemStore.getState();
                        addActivity({
                            agent: payload?.agent,
                            message: payload?.message || payload?.text || "Activity",
                            tool: payload?.tool,
                            timestamp: new Date().toISOString()
                        });
                        break;
                    }
                    case "error_events": {
                        const { setError, addActivity } = useAgentSystemStore.getState();
                        const message = payload?.message || "Error";
                        setError(message);
                        addActivity({
                            agent: payload?.agent,
                            message,
                            timestamp: new Date().toISOString(),
                            level: "error"
                        });
                        break;
                    }
                    case "tts_started": {
                        const { setState } = useAgentSystemStore.getState();
                        setState("speaking");
                        break;
                    }
                    case "tts_finished": {
                        const { setState } = useAgentSystemStore.getState();
                        setState("idle");
                        break;
                    }
                    case "orchestrator_state_update":
                        this.handleOrchestratorStateUpdate(payload.state);
                        break;

                    case "assistant_response":
                        if (payload.text) {
                            ttsEngine.handleFinal(task_id || this.currentTaskId, payload.text);
                        }
                        this.currentTaskId = null;
                        this.stateManager.updateData({ taskId: null });
                        break;

                    case "assistant_text_chunk":
                        if (payload.text) {
                            ttsEngine.handleChunk(task_id || this.currentTaskId, payload.text);
                        }
                        break;

                    case "clarification_required":
                        this.stateManager.transitionTo(AssistantState.CLARIFICATION_REQUIRED, {
                            clarification: {
                                question_text: payload.question_text
                            }
                        });
                        if (payload.question_text) {
                            this.shouldListenAfterTts = true;
                            ttsEngine.speak(payload.question_text, { interrupt: true });
                        }
                        // If it has "use_tts": true, audio should be streaming/playing.
                        // We will auto-transition to LISTENING after audio ends in handleUserSpeechStart/End logic
                        // But wait, if backend sends audio, we play it. 
                        // Once audio finishes, we should listen.
                        // The AudioPlayer needs to tell us when it stops? 
                        // For now, let's assuming user manually replies or we use VAD after TTS.
                        // A robust way: set state to CLARIFICATION, play audio. 
                        // When audio finishes -> Auto LISTENING?
                        break;

                    case "system_permission_required":
                        this.stateManager.transitionTo(AssistantState.PERMISSION_REQUIRED, {
                            permission: {
                                command_summary: payload.command_summary,
                                exact_operation: payload.exact_operation,
                                risk_level: payload.risk_level,
                                source: "system"
                            }
                        });
                        if (payload.command_summary) {
                            ttsEngine.speak(`Permission required. ${payload.command_summary}`, { interrupt: true });
                        }
                        break;

                    case "autonomous_task_started":
                        if (payload?.query) {
                            ttsEngine.speak(`Starting: ${payload.query}`, { interrupt: true });
                        }
                        break;

                    case "autonomous_task_notice":
                        if (payload?.query) {
                            ttsEngine.speak(`Heads up: ${payload.query}`, { interrupt: true });
                        }
                        break;

                    case "autonomous_task_result":
                        break;

                    case "autonomous_permission_required":
                        this.stateManager.transitionTo(AssistantState.PERMISSION_REQUIRED, {
                            permission: {
                                command_summary: payload.query || "Autonomous action requested",
                                exact_operation: payload.query || "",
                                risk_level: payload.risk_level || "unknown",
                                request_id: payload.request_id,
                                source: "autonomous",
                                query: payload.query
                            }
                        });
                        if (payload?.query) {
                            ttsEngine.speak(`Permission required. ${payload.query}`, { interrupt: true });
                        }
                        break;

                    case "orchestrator_error":
                        ttsEngine.stop();
                        this.stateManager.transitionTo(AssistantState.IDLE);
                        this.currentTaskId = null;
                        this.stateManager.updateData({ taskId: null });
                        break;

                    case "reminder_triggered":
                    case "alarm_triggered":
                        if (payload?.text) {
                            ttsEngine.speak(payload.text, { interrupt: true });
                        } else if (payload?.label) {
                            ttsEngine.speak(payload.label, { interrupt: true });
                        } else {
                            ttsEngine.speak("Reminder triggered.", { interrupt: true });
                        }
                        break;
                }

            } catch (e) {
                console.error("[Brain] Error processing message:", e);
            }
        });

        // Setup audio listener to know when speaking ends
        // We can poll or add a callback if AudioPlayer supports it.
        // For now, relying on VAD to barge-in or manual state management.
    }

    public async handleUserSpeechStart() {
        const currentState = this.stateManager.getCurrentState();
        const isAssistantSpeaking = currentState === AssistantState.SPEAKING || ttsEngine.isSpeaking;
        const isAssistantThinking = currentState === AssistantState.THINKING;

        if (this.turnManager.shouldInterrupt(true, isAssistantSpeaking, isAssistantThinking)) {
            console.log("[Brain] Interruption detected! Stopping audio/processing.");
            ttsEngine.stop();
            this.stateManager.transitionTo(AssistantState.INTERRUPTED);

            // Send interrupt to backend
            if (this.currentTaskId) {
                const { AgentCommunication } = await import("../lib/client_websocket");
                AgentCommunication.sendJSON({
                    type: "interrupt",
                    task_id: this.currentTaskId,
                });
            }
        }

        // If we are in CLARIFICATION state, we expect user speech, so we transition to listening (if not already)
        if (currentState === AssistantState.CLARIFICATION_REQUIRED) {
            this.stateManager.transitionTo(AssistantState.LISTENING);
        }
        else if (currentState === AssistantState.IDLE) {
            this.stateManager.transitionTo(AssistantState.LISTENING);
        }
    }

    public handleUserSpeechEnd(text: string) {
        this.turnManager.noteUserSpeechEnd();
        const currentState = this.stateManager.getCurrentState();
        const stateData = this.stateManager.getData();

        if (currentState === AssistantState.LISTENING ||
            currentState === AssistantState.IDLE ||
            currentState === AssistantState.INTERRUPTED ||
            currentState === AssistantState.CLARIFICATION_REQUIRED) { // Allow speaking in clarification

            // Logic to determine if we should send this text
            // If we were interrupted, we treat this as a new query or the interruption command.

            // Check if we are answering a clarification
            if (stateData.taskId && currentState === AssistantState.CLARIFICATION_REQUIRED ||
                (stateData.taskId && currentState === AssistantState.LISTENING)) {
                // It's likely a clarification response if we have a task ID and were just asked?
                // Actually, check if we have a pending clarification question?
                // Or better, if we have a task_id and are in listening mode, check if backend asked for something.
                // The backend state "clarification_required" puts usage in that mode.
                // But if we moved to LISTENING, we might have lost that specific enum value if we just overwrite it.
                // However, we can check stateData.taskId.

                // Ideally, if we are in CLARIFICATION_REQUIRED, we stay there until resolved?
                // No, we need to listen. 

                if (stateData.clarification) {
                    this.sendClarificationResponse(stateData.taskId!, text);
                    // Clear clarification data
                    this.stateManager.updateData({ clarification: null });
                    return;
                }
            }

            // Default: New Query
            this.processQuery(text);
        }
    }

    public async respondToPermission(approved: boolean) {
        const data = this.stateManager.getData();
        if (data.taskId) {
            const { AgentCommunication } = await import("../lib/client_websocket");
            if (data.permission?.source === "autonomous" && data.permission?.request_id) {
                AgentCommunication.sendJSON({
                    type: "autonomous_permission_response",
                    payload: {
                        request_id: data.permission.request_id,
                        approved: approved
                    }
                });
            } else {
                AgentCommunication.sendJSON({
                    type: "permission_response",
                    payload: {
                        task_id: data.taskId,
                        approved: approved
                    }
                });
            }
            // Clear permission data and transition to thinking
            this.stateManager.updateData({ permission: null });
            this.stateManager.transitionTo(AssistantState.THINKING);
        }
    }

    public async respondToClarification(text: string) {
        // Manual text entry fallback
        const data = this.stateManager.getData();
        if (data.taskId) {
            this.sendClarificationResponse(data.taskId, text);
        }
    }

    // Internal Logic
    private async processQuery(text: string) {
        this.stateManager.transitionTo(AssistantState.THINKING);
        ttsEngine.stop();

        const requestId = `req_${Date.now()}`;
        const token = localStorage.getItem("jarvis:token") || "";
        const baseUrl = localStorage.getItem('jarvis:selectedServer') || "http://localhost:8080";

        const { AgentCommunication } = await import("../lib/client_websocket");

        AgentCommunication.sendJSON({
            type: "user_query",
            request_id: requestId,
            payload: {
                name: "Voice Command", // legacy
                text: text, // Correct protocol field
                auth_token: token,
                base_url: baseUrl
            },
            metadata: {
                task_type: "voice_command",
                source: "audio_transcription"
            }
        });
    }

    private async sendClarificationResponse(taskId: string, text: string) {
        this.stateManager.transitionTo(AssistantState.THINKING);
        const { AgentCommunication } = await import("../lib/client_websocket");
        AgentCommunication.sendJSON({
            type: "clarification_response",
            payload: {
                task_id: taskId,
                text: text
            }
        });
    }

    private handleOrchestratorStateUpdate(state: string) {
        switch (state) {
            case "thinking":
                this.stateManager.transitionTo(AssistantState.THINKING);
                break;
            case "streaming":
                this.stateManager.transitionTo(AssistantState.SPEAKING);
                break;
            case "paused":
                this.stateManager.transitionTo(AssistantState.PAUSED);
                break;
            case "cancelled":
                this.stateManager.transitionTo(AssistantState.IDLE);
                break;
            case "idle":
                this.stateManager.transitionTo(AssistantState.IDLE);
                break;
            case "completed":
            case "failed":
            case "interrupted":
                this.stateManager.transitionTo(AssistantState.IDLE);
                break;
        }
    }

    // Accessors
    public getState() {
        return useBrainState.getState().currentState;
    }

    public getBrainData() {
        return useBrainState.getState().data;
    }
}

export const brain = JarvisBrain.getInstance();
