export type DialogueAction =
    | { type: "PROCESS_QUERY"; text: string }
    | { type: "STOP_SPEAKING" }
    | { type: "IGNORE" };

export class DialogueManager {

    public decide(text: string, isSpeaking: boolean): DialogueAction {
        const trimmed = text.trim().toLowerCase();

        if (!trimmed) {
            return { type: "IGNORE" };
        }

        // Local command handling (example)
        if (trimmed === "stop" || trimmed === "silence" || trimmed === "shh") {
            return { type: "STOP_SPEAKING" };
        }

        // Default: Process as query
        return { type: "PROCESS_QUERY", text: text };
    }
}
