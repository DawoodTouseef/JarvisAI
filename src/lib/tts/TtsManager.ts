type TtsCallbacks = {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: unknown) => void;
};

type SpeakOptions = {
  interrupt?: boolean;
  taskId?: string;
};

type OpenAiTtsConfig = {
  apiKey: string;
  baseUrl: string;
  model: string;
  voice: string;
  timeoutMs: number;
};

type QueueItem = {
  text: string;
  taskId?: string;
};

const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_OPENAI_MODEL = "gpt-4o-mini-tts";
const DEFAULT_OPENAI_VOICE = "alloy";
const DEFAULT_OPENAI_TIMEOUT_MS = 12000;

const PUNCT_START = /^[,.;:!?]/;

const normalizeWhitespace = (text: string) => text.replace(/\s+/g, " ").trim();

const needsLeadingSpace = (currentText: string, nextChunk: string) => {
  if (!currentText) return false;
  const prevChar = currentText[currentText.length - 1];
  if (!prevChar || /\s/.test(prevChar)) return false;
  if (!nextChunk) return false;
  return !PUNCT_START.test(nextChunk);
};

class StreamBuffer {
  public hasChunks = false;
  private fullText = "";
  private pending = "";
  private lastRawChunk = "";
  private lastUpdateAt = 0;

  public ingestChunk(rawChunk: string): string | null {
    const trimmed = rawChunk.trim();
    if (!trimmed) return null;

    const now = Date.now();
    if (trimmed === this.lastRawChunk && now - this.lastUpdateAt < 500) {
      return null;
    }

    this.lastRawChunk = trimmed;
    this.lastUpdateAt = now;

    let delta = trimmed;
    const normalizedFull = normalizeWhitespace(this.fullText);

    if (this.fullText && trimmed.startsWith(this.fullText)) {
      delta = trimmed.slice(this.fullText.length);
    } else if (normalizedFull && trimmed.startsWith(normalizedFull)) {
      delta = trimmed.slice(normalizedFull.length);
    }

    const normalizedDelta = delta.trim();
    if (!normalizedDelta) return null;

    let toAppend = normalizedDelta;
    if (needsLeadingSpace(this.fullText, toAppend)) {
      toAppend = ` ${toAppend}`;
    }

    this.fullText += toAppend;
    this.pending += toAppend;
    this.hasChunks = true;

    const shouldFlush =
      this.pending.length >= 140 ||
      /[.!?]\s$/.test(this.pending) ||
      this.pending.includes("\n");

    return shouldFlush ? this.flush() : null;
  }

  public flush(): string | null {
    const trimmed = this.pending.trim();
    this.pending = "";
    return trimmed || null;
  }

  public finalize(finalText: string): string[] {
    const segments: string[] = [];
    const pending = this.flush();
    if (pending) segments.push(pending);

    if (!this.hasChunks) {
      const finalTrimmed = finalText.trim();
      if (finalTrimmed) segments.push(finalTrimmed);
      return segments;
    }

    const finalTrimmed = finalText.trim();
    if (!finalTrimmed) return segments;

    const normalizedFinal = normalizeWhitespace(finalTrimmed);
    const normalizedSoFar = normalizeWhitespace(this.fullText);

    if (normalizedFinal.startsWith(normalizedSoFar)) {
      const delta = normalizedFinal.slice(normalizedSoFar.length).trim();
      if (delta) segments.push(delta);
    }

    return segments;
  }
}

class WebSpeechEngine {
  private synth: SpeechSynthesis | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private voiceName: string | null = null;
  private current: SpeechSynthesisUtterance | null = null;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.synth = window.speechSynthesis;
      this.refreshVoices();
      this.synth.onvoiceschanged = () => this.refreshVoices();
    }
  }

  public setVoiceByName(name: string) {
    this.voiceName = name;
  }

  public get isSpeaking(): boolean {
    if (!this.synth) return false;
    return this.synth.speaking || this.synth.pending || !!this.current;
  }

  public async play(text: string): Promise<void> {
    if (!this.synth) return;

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = this.getPreferredVoice();
    if (voice) utterance.voice = voice;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    this.current = utterance;

    await new Promise<void>((resolve, reject) => {
      utterance.onend = () => {
        this.current = null;
        resolve();
      };
      utterance.onerror = (e) => {
        this.current = null;
        reject(e);
      };
      this.synth?.speak(utterance);
    });
  }

  public stop() {
    if (this.synth && (this.synth.speaking || this.synth.pending)) {
      this.synth.cancel();
    }
    this.current = null;
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
}

class OpenAiTtsEngine {
  private currentAudio: HTMLAudioElement | null = null;
  private currentAbort: AbortController | null = null;
  private abortReason: "timeout" | "stop" | null = null;

  public getAbortReason() {
    return this.abortReason;
  }

  public async play(text: string, config: OpenAiTtsConfig): Promise<void> {
    const controller = new AbortController();
    this.currentAbort = controller;
    this.abortReason = null;

    const timeoutId = setTimeout(() => {
      this.abortReason = "timeout";
      controller.abort();
    }, config.timeoutMs);

    try {
      const response = await fetch(`${localStorage.getItem("jarvis:selectedServer")}/audio/speech`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem('jarvis:token')}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: config.model,
          input: text,
          voice: config.voice,
          response_format: "mp3"
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`OpenAI TTS failed (${response.status})`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);

      await this.playAudioUrl(url);
    } finally {
      clearTimeout(timeoutId);
      this.currentAbort = null;
    }
  }

  public stop() {
    if (this.currentAbort) {
      this.abortReason = "stop";
      this.currentAbort.abort();
      this.currentAbort = null;
    }

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
  }

  private async playAudioUrl(url: string): Promise<void> {
    const audio = new Audio(url);
    this.currentAudio = audio;

    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        URL.revokeObjectURL(url);
        if (this.currentAudio === audio) {
          this.currentAudio = null;
        }
      };

      audio.onended = () => {
        cleanup();
        resolve();
      };
      audio.onerror = () => {
        cleanup();
        reject(new Error("OpenAI audio playback failed"));
      };
      audio.play().catch((err) => {
        cleanup();
        reject(err);
      });
    });
  }
}

const resolveOpenAiConfig = (): OpenAiTtsConfig | null => {
  const envKey = import.meta.env.VITE_OPENAI_API_KEY as string | undefined;
  const storedKey =
    typeof window !== "undefined" ? window.localStorage.getItem("jarvis:token") || "" : "";

  const apiKey = envKey || storedKey;
  if (!apiKey) return null;

  const baseUrl = (import.meta.env.VITE_OPENAI_BASE_URL as string | undefined) || DEFAULT_OPENAI_BASE_URL;
  const model = (import.meta.env.VITE_OPENAI_TTS_MODEL as string | undefined) || DEFAULT_OPENAI_MODEL;
  const voice = (import.meta.env.VITE_OPENAI_TTS_VOICE as string | undefined) || DEFAULT_OPENAI_VOICE;
  const timeoutMsRaw = import.meta.env.VITE_OPENAI_TTS_TIMEOUT_MS as string | undefined;
  const timeoutMs = timeoutMsRaw ? Number(timeoutMsRaw) : DEFAULT_OPENAI_TIMEOUT_MS;

  return {
    apiKey,
    baseUrl,
    model,
    voice,
    timeoutMs: Number.isFinite(timeoutMs) ? timeoutMs : DEFAULT_OPENAI_TIMEOUT_MS
  };
};

class TtsManager {
  private callbacks = new Set<TtsCallbacks>();
  private webEngine = new WebSpeechEngine();
  private openaiEngine = new OpenAiTtsEngine();
  private queue: QueueItem[] = [];
  private current: QueueItem | null = null;
  private buffers = new Map<string, StreamBuffer>();
  private speaking = false;
  private forceWebFallback = false;
  private playToken = 0;

  public setCallbacks(callbacks: TtsCallbacks) {
    this.callbacks.clear();
    this.callbacks.add(callbacks);
  }

  public addCallbacks(callbacks: TtsCallbacks) {
    this.callbacks.add(callbacks);
  }

  public removeCallbacks(callbacks: TtsCallbacks) {
    this.callbacks.delete(callbacks);
  }

  public get isSpeaking(): boolean {
    return this.speaking || this.queue.length > 0;
  }

  public speak(text: string, options: SpeakOptions = {}) {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (options.interrupt !== false) {
      this.stop();
    }

    this.enqueue({ text: trimmed, taskId: options.taskId });
  }

  public handleChunk(taskId: string | null, text: string) {
    if (!taskId) return;
    const buffer = this.getBuffer(taskId);
    const segment = buffer.ingestChunk(text);
    if (segment) {
      this.enqueue({ text: segment, taskId });
    }
  }

  public handleFinal(taskId: string | null, text: string) {
    if (!taskId) {
      this.speak(text, { interrupt: true });
      return;
    }

    const buffer = this.getBuffer(taskId);
    const segments = buffer.finalize(text);
    const hadChunks = buffer.hasChunks;

    this.buffers.delete(taskId);

    if (!segments.length) return;

    if (!hadChunks) {
      this.stop();
    }

    for (const segment of segments) {
      this.enqueue({ text: segment, taskId });
    }
  }

  public cancelCurrentTask(taskId?: string | null) {
    if (!taskId) return;
    this.buffers.delete(taskId);
    this.queue = this.queue.filter((item) => item.taskId !== taskId);
    if (this.current?.taskId === taskId) {
      this.stop();
    }
  }

  public stop() {
    this.playToken += 1;
    this.queue = [];
    this.current = null;
    this.buffers.clear();
    this.webEngine.stop();
    this.openaiEngine.stop();
    if (this.speaking) {
      this.speaking = false;
      this.emitEnd();
    }
  }

  private getBuffer(taskId: string) {
    const existing = this.buffers.get(taskId);
    if (existing) return existing;
    const buffer = new StreamBuffer();
    this.buffers.set(taskId, buffer);
    return buffer;
  }

  private enqueue(item: QueueItem) {
    this.queue.push(item);
    this.processQueue();
  }

  private async processQueue() {
    if (this.current) return;
    const next = this.queue.shift();
    if (!next) {
      if (this.speaking) {
        this.speaking = false;
        this.emitEnd();
      }
      return;
    }

    this.current = next;
    const token = this.playToken;

    if (!this.speaking) {
      this.speaking = true;
      this.emitStart();
    }

    try {
      await this.playItem(next);
    } catch (err) {
      if (token === this.playToken) {
        this.emitError(err);
      }
    } finally {
      if (token !== this.playToken) {
        this.current = null;
        return;
      }
      this.current = null;
      this.processQueue();
    }
  }

  private async playItem(item: QueueItem) {
    const config = resolveOpenAiConfig();

    if (config && !this.forceWebFallback) {
      try {
        await this.openaiEngine.play(item.text, config);
        return;
      } catch (err) {
        const isAbort =
          typeof err === "object" &&
          err !== null &&
          "name" in err &&
          (err as { name?: string }).name === "AbortError";

        const abortReason = this.openaiEngine.getAbortReason();
        if (isAbort && abortReason === "stop") {
          throw err;
        }

        this.forceWebFallback = true;
        this.emitError(err);
      }
    }

    await this.webEngine.play(item.text);
  }

  private emitStart() {
    for (const cb of this.callbacks) cb.onStart?.();
  }

  private emitEnd() {
    for (const cb of this.callbacks) cb.onEnd?.();
  }

  private emitError(error: unknown) {
    for (const cb of this.callbacks) cb.onError?.(error);
  }
}

export const ttsEngine = new TtsManager();
export type { TtsCallbacks, SpeakOptions };
