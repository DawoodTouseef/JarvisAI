export class StreamingAudioPlayer {
    private audioContext: AudioContext;
    private nextStartTime: number = 0;
    private isConnected: boolean = false;
    private queue: AudioBufferSourceNode[] = [];
    private isPlaying: boolean = false;

    constructor() {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    private ensureContext() {
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }

    public async playChunk(data: ArrayBuffer) {
        this.ensureContext();

        try {
            const buffer = await this.audioContext.decodeAudioData(data.slice(0));
            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.audioContext.destination);

            // Schedule play
            // If nextStartTime is in the past, play "now".
            const now = this.audioContext.currentTime;
            // Add a small buffer only if we are starting fresh to avoid glitches
            const start = Math.max(now, this.nextStartTime);

            source.start(start);
            this.nextStartTime = start + buffer.duration;

            this.queue.push(source);

            // Cleanup when done
            source.onended = () => {
                const index = this.queue.indexOf(source);
                if (index > -1) {
                    this.queue.splice(index, 1);
                }
            };

            this.isPlaying = true;

        } catch (error) {
            console.error("Error decoding audio chunk:", error);
        }
    }

    public stop() {
        // Stop all currently scheduled sources
        this.queue.forEach(source => {
            try {
                source.stop();
                source.disconnect();
            } catch (e) {
                // ignore errors if already stopped
            }
        });
        this.queue = [];
        this.nextStartTime = 0;
        this.isPlaying = false;

        // Reset context time reference effectively by allowing next play to start at currentTime
        // (nextStartTime is already 0, so logic in playChunk handles it)
    }

    public get isActive(): boolean {
        return this.isPlaying || this.queue.length > 0;
    }
}

export const audioPlayer = new StreamingAudioPlayer();
