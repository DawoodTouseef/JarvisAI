import { BrainConfig } from "./types";

export class TurnManager {
    private config: BrainConfig;
    private lastSpeechTimestamp: number = 0;

    constructor(config: BrainConfig) {
        this.config = config;
    }

    public shouldInterrupt(isUserSpeaking: boolean, isAssistantSpeaking: boolean, isAssistantThinking: boolean): boolean {
        if (!this.config.bargeInEnabled) return false;

        // Interrupt if assistant is speaking OR thinking
        if (isUserSpeaking && (isAssistantSpeaking || isAssistantThinking)) {
            return true;
        }
        return false;
    }

    public noteUserSpeechEnd() {
        this.lastSpeechTimestamp = Date.now();
    }

    public isSilenceTimeoutExceeded(currentTimestamp: number): boolean {
        if (this.lastSpeechTimestamp === 0) return false;
        return (currentTimestamp - this.lastSpeechTimestamp) > this.config.silenceTimeoutMs;
    }
}
