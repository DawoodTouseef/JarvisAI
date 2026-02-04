type TtsCallbacks = {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: unknown) => void;
};

type SpeakOptions = {
  interrupt?: boolean;
};

export class SpeechSynthesisTTS {
  private synth: SpeechSynthesis | null = null;
  private voiceName: string | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private queue: SpeechSynthesisUtterance[] = [];
  private current: SpeechSynthesisUtterance | null = null;
  private buffer: string = "";
  private callbacks: TtsCallbacks = {};

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.synth = window.speechSynthesis;
      this.refreshVoices();
      this.synth.onvoiceschanged = () => this.refreshVoices();
    }
  }

  public setCallbacks(callbacks: TtsCallbacks) {
    this.callbacks = callbacks;
  }

  public setVoiceByName(name: string) {
    this.voiceName = name;
  }

  public get isSpeaking(): boolean {
    if (!this.synth) return false;
    return this.synth.speaking || this.synth.pending || this.queue.length > 0 || !!this.current;
  }

  public speak(text: string, options: SpeakOptions = {}) {
    const trimmed = text.trim();
    if (!trimmed || !this.synth) return;
    if (options.interrupt !== false) {
      this.stop();
    }
    this.enqueue(trimmed);
  }

  public appendChunk(text: string, isFinal = false) {
    if (!this.synth) return;
    this.buffer += text;
    if (isFinal) {
      this.flush();
      return;
    }

    const shouldFlush =
      this.buffer.length >= 180 ||
      /[.!?]\s$/.test(this.buffer) ||
      this.buffer.includes("\n");

    if (shouldFlush) {
      this.flush();
    }
  }

  public flush() {
    const trimmed = this.buffer.trim();
    this.buffer = "";
    if (!trimmed || !this.synth) return;
    this.enqueue(trimmed);
  }

  public stop() {
    this.buffer = "";
    this.queue = [];
    this.current = null;
    if (this.synth && (this.synth.speaking || this.synth.pending)) {
      this.synth.cancel();
    }
    this.callbacks.onEnd?.();
  }

  private refreshVoices() {
    if (!this.synth) return;
    this.voices = this.synth.getVoices();
  }

  private getPreferredVoice(): SpeechSynthesisVoice | null {
    if (!this.voices.length) return null;
    if (this.voiceName) {
      const match = this.voices.find((v) => v.name === this.voiceName);
      if (match) return match;
    }
    const english = this.voices.find((v) => v.lang.toLowerCase().startsWith("en"));
    return english || this.voices[0];
  }

  private enqueue(text: string) {
    if (!this.synth) return;
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = this.getPreferredVoice();
    if (voice) utterance.voice = voice;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
      if (!this.isSpeaking) {
        this.callbacks.onStart?.();
      } else {
        this.callbacks.onStart?.();
      }
    };
    utterance.onend = () => {
      if (this.current === utterance) {
        this.current = null;
      }
      if (!this.queue.length) {
        this.callbacks.onEnd?.();
      }
      this.processQueue();
    };
    utterance.onerror = (e) => {
      this.callbacks.onError?.(e);
      if (this.current === utterance) {
        this.current = null;
      }
      this.processQueue();
    };

    this.queue.push(utterance);
    this.processQueue();
  }

  private processQueue() {
    if (!this.synth || this.synth.speaking || this.current) return;
    const next = this.queue.shift();
    if (!next) return;
    this.current = next;
    this.synth.speak(next);
  }
}

export const ttsEngine = new SpeechSynthesisTTS();
