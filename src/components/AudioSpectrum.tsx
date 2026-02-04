import { useRef, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { toast } from "sonner";
import { useTranscriptionStore } from "@/stores/transcription";
import { AgentCommunication, WakeWordCommunication } from '@/lib/client_websocket';
import { brain, AssistantState, useBrainState } from '@/brain';
import { useSpeakingStore } from "@/stores/speaking";
import { ttsEngine } from "@/lib/tts/TtsManager";

type VoiceState = "IDLE" | "LISTENING" | "PROCESSING" | "SPEAKING" | "RESET";

const ListeningAnimation = ({ isTranscribing, voiceState }: { isTranscribing: boolean; voiceState: VoiceState; }) => {
  const text = isTranscribing
    ? "TRANSCRIBING..."
    : voiceState === "SPEAKING"
      ? "SPEAKING..."
      : voiceState === "LISTENING"
        ? "LISTENING..."
        : voiceState === "PROCESSING"
          ? "PROCESSING..."
          : voiceState === "RESET"
            ? "RESETTING..."
            : "AWAITING VOICE COMMAND";

  const chars = text.split('  ');

  const container = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.02 } },
  } as const;

  const child = {
    hidden: { opacity: 0, y: 6 },
    visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 400, damping: 24 } },
  } as const;

  const isListening = voiceState === "LISTENING";

  return (
    <motion.p
      className={`font-orbitron text-sm tracking-wider ${isTranscribing ? 'text-primary shimmer-text glow-text animate-flicker' : isListening ? 'text-primary glow-text animate-pulse-glow' : 'text-primary glow-text'}`}
      variants={container}
      initial="hidden"
      animate="visible"
      aria-live="polite"
    >

      {chars.map((c, i) => (
        <motion.span key={i} className="inline-block" variants={child}>
          {c}
        </motion.span>
      ))}

    </motion.p>
  );
}
export const AudioSpectrum = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);
  const animationRef = useRef<number>();
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [voiceState, setVoiceState] = useState<VoiceState>("IDLE");
  const voiceStateRef = useRef<VoiceState>("IDLE");
  const wakeWordEnabledRef = useRef(true);
  const vadEnabledRef = useRef(true);
  const resetInProgressRef = useRef(false);
  const skipTranscriptionRef = useRef(false);
  const bargeInRef = useRef(false);
  const chunksRef = useRef<Blob[]>([]);
  const url = localStorage.getItem('jarvis:selectedServer') || '';

  // hotword scanning state
  const [wakeStatus, setWakeStatus] = useState<string>("AWAITING WAKE WORD");

  // Global transcription available throughout the app
  const transcriptions = useTranscriptionStore((s) => s.text);
  const setTranscription = useTranscriptionStore((s) => s.setText);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const setIsUserSpeaking = useSpeakingStore((s) => s.setText);
  const isListening = voiceState === "LISTENING";

  // New state for dialogs
  const [clarificationReq, setClarificationReq] = useState<{ task_id: string, question: string } | null>(null);
  const [permissionReq, setPermissionReq] = useState<{ task_id: string, summary: string, operation: string, risk: string } | null>(null);

  const transitionTo = useCallback((next: VoiceState, reason?: string) => {
    const current = voiceStateRef.current;
    if (current === next) return;
    const allowed: Record<VoiceState, VoiceState[]> = {
      IDLE: ["LISTENING", "RESET"],
      LISTENING: ["PROCESSING", "SPEAKING", "RESET"],
      PROCESSING: ["SPEAKING", "RESET", "IDLE", "LISTENING"],
      SPEAKING: ["RESET", "LISTENING"],
      RESET: ["IDLE", "LISTENING"]
    };

    if (!allowed[current].includes(next)) {
      console.warn(`[VoiceState] Invalid transition ${current} -> ${next}${reason ? ` (${reason})` : ""}`);
    }

    voiceStateRef.current = next;
    setVoiceState(next);
  }, []);

  const drawSpectrum = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.6;

    // Clear with fade effect for trails
    ctx.fillStyle = "transparent";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const bars = 128; // Increased resolution
    const dataArray = new Uint8Array(bars);

    // Get State
    const brainState = brain.getState();
    const isThinking = brainState === AssistantState.THINKING;
    const isSpeakingState = voiceState === "SPEAKING";
    const isListeningState = voiceState === "LISTENING";

    if (analyser && (isListeningState || isSpeakingState)) {
      analyser.fftSize = 512; // Higher FFT size for better resolution
      const tempArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(tempArray);

      // Interpolate to fit bars count
      const step = Math.floor(tempArray.length / bars);
      for (let i = 0; i < bars; i++) {
        let val = 0;
        for (let j = 0; j < step; j++) {
          val += tempArray[i * step + j];
        }
        dataArray[i] = val / step;
      }
    } else {
      // Synthetic data for Idle / Thinking
      const time = Date.now() / 1000;
      for (let i = 0; i < bars; i++) {
        if (isThinking) {
          // Fast rotating wave for thinking
          dataArray[i] = 50 + Math.sin(time * 10 + i * 0.5) * 30;
        } else {
          // Slow breathing for idle
          dataArray[i] = 20 + Math.sin(time * 2 + i * 0.2) * 10;
        }
      }
    }

    // Colors based on state
    let baseHue = 185; // Cyan (Default)
    if (isThinking) baseHue = 280; // Purple
    if (isSpeakingState) baseHue = 140; // Green
    if (wakeStatus === 'WAKE WORD DETECTED') baseHue = 30; // Orange

    // Draw circular spectrum
    for (let i = 0; i < bars; i++) {
      const angle = (i / bars) * Math.PI * 2 - Math.PI / 2 + (isThinking ? Date.now() / 500 : 0); // Rotate if thinking
      const value = dataArray[i] || 0;

      // Scale bar height based on state responsiveness
      let barHeight = (value / 255) * radius * 0.8 + 5;
      if (isSpeakingState) barHeight *= 1.2;

      const innerRadius = radius * 0.45;
      const x1 = centerX + Math.cos(angle) * innerRadius;
      const y1 = centerY + Math.sin(angle) * innerRadius;
      const x2 = centerX + Math.cos(angle) * (innerRadius + barHeight);
      const y2 = centerY + Math.sin(angle) * (innerRadius + barHeight);

      // Gradient for bars
      const gradient = ctx.createLinearGradient(x1, y1, x2, y2);
      gradient.addColorStop(0, `hsla(${baseHue}, 100%, 50%, 0.6)`);
      gradient.addColorStop(0.5, `hsla(${baseHue}, 100%, 60%, 0.8)`);
      gradient.addColorStop(1, `hsla(${baseHue + 20}, 100%, 60%, 0.9)`);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = isThinking ? 2 : 3;
      ctx.lineCap = "round";
      ctx.stroke();

      // Glow effect (optimized: only draw for loud bars or specific states)
      if (value > 100 || isThinking) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `hsla(${baseHue}, 100%, 50%, ${0.1 + (value / 255) * 0.2})`;
        ctx.lineWidth = 6;
        ctx.lineCap = "round";
        ctx.stroke();
      }
    }

    // Draw inner circle (Core)
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.4, 0, Math.PI * 2);
    ctx.strokeStyle = `hsla(${baseHue}, 100%, 50%, 0.3)`;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw pulsing center
    const pulseScale = 1 + Math.sin(Date.now() / (isThinking ? 200 : 500)) * (isSpeakingState ? 0.3 : 0.1);
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.15 * pulseScale, 0, Math.PI * 2);
    const centerGradient = ctx.createRadialGradient(
      centerX, centerY, 0,
      centerX, centerY, radius * 0.2 * pulseScale
    );
    centerGradient.addColorStop(0, `hsla(${baseHue}, 100%, 60%, 0.8)`);
    centerGradient.addColorStop(1, `hsla(${baseHue}, 100%, 50%, 0.0)`);
    ctx.fillStyle = centerGradient;
    ctx.fill();

    animationRef.current = requestAnimationFrame(drawSpectrum);
  }, [analyser, voiceState, wakeStatus]);

  useEffect(() => {
    animationRef.current = requestAnimationFrame(drawSpectrum);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [drawSpectrum]);

  /*
   * Brain Integration: Transcription Logic
   */
  const handleTranscription = (text: string) => {
    try {
      brain.handleUserSpeechEnd(text);
      toast.info(`Heard: "${text}"`);
    } catch (err) {
      console.error('Failed to process transcription via Brain', err);
    }
  };

  const transcription = async (audioBlob: Blob) => {
    if (!url) {
      toast.error('No server selected. Please select a server on the Services page.');
      setIsTranscribing(false);
      return;
    }

    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');
    setIsTranscribing(true);
    try {
      const response = await fetch(`${url}/api/v1/audio/transcriptions`, {
        method: 'POST',
        body: formData,
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("jarvis:token") || sessionStorage.getItem("jarvis:token") || ''}`
        }
      });

      if (!response.ok) {
        const text = await response.json();
        toast.error("Error during transcription: " + (text.detail || `HTTP error! status: ${response.status}`));
      }
      else {
        const data = await response.json();

        // Update global store
        setTranscription([...transcriptions, { text: data.text, updated: new Date() }]);

        // Notify brain with the text
        handleTranscription(data.text);
      }
    } catch (error) {
      console.error("Error during transcription:", error);
      toast.error("Failed to transcribe audio.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const teardownMicPipeline = useCallback(async () => {
    try {
      const mr = mediaRecorderRef.current;
      if (mr && mr.state === "recording") {
        skipTranscriptionRef.current = true;
        mr.stop();
      }
      mediaRecorderRef.current = null;

      if (scriptNodeRef.current) {
        scriptNodeRef.current.onaudioprocess = null;
        scriptNodeRef.current.disconnect();
        scriptNodeRef.current = null;
      }

      if (sourceRef.current) {
        sourceRef.current.disconnect();
        sourceRef.current = null;
      }

      if (analyserRef.current) {
        analyserRef.current.disconnect();
        analyserRef.current = null;
        setAnalyser(null);
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      if (audioContextRef.current) {
        try {
          await audioContextRef.current.close();
        } catch (err) {
          console.warn("AudioContext close failed:", err);
        }
        audioContextRef.current = null;
      }
    } catch (err) {
      console.warn("Mic teardown failed:", err);
    }
  }, []);

  const initMicPipeline = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const ctx = new AudioContext();
    audioContextRef.current = ctx;

    const anl = ctx.createAnalyser();
    anl.fftSize = 256;
    analyserRef.current = anl;
    setAnalyser(anl);

    const source = ctx.createMediaStreamSource(stream);
    sourceRef.current = source;
    source.connect(anl);

    const downsample = (pcm: Float32Array, inRate: number) => {
      const outRate = 16000;
      const ratio = inRate / outRate;
      const newLen = Math.round(pcm.length / ratio);
      const out = new Int16Array(newLen);
      for (let i = 0; i < newLen; i++) {
        const idx = Math.round(i * ratio);
        let s = Math.max(-1, Math.min(1, pcm[idx]));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      return out;
    };

    const scriptNode = ctx.createScriptProcessor(4096, 1, 1);
    scriptNodeRef.current = scriptNode;
    scriptNode.onaudioprocess = (e) => {
      if (!wakeWordEnabledRef.current) return;
      if (voiceStateRef.current !== "IDLE") return;
      const input = e.inputBuffer.getChannelData(0);
      const pcm16 = downsample(input, ctx.sampleRate);
      WakeWordCommunication.sendBytes(pcm16.buffer);
    };

    source.connect(scriptNode);
    scriptNode.connect(ctx.destination);
  }, []);

  const restartMicPipeline = useCallback(async () => {
    await teardownMicPipeline();
    await initMicPipeline();
  }, [initMicPipeline, teardownMicPipeline]);

  const ensureMicPipeline = useCallback(async () => {
    if (!streamRef.current || !audioContextRef.current) {
      await initMicPipeline();
    }
    if (audioContextRef.current?.state === "suspended") {
      await audioContextRef.current.resume();
    }
  }, [initMicPipeline]);

  const startListening = useCallback(async () => {
    try {
      await ensureMicPipeline();

      // Reset chunks for new recording
      chunksRef.current = [];

      const stream = streamRef.current;
      if (stream) {
        const mr = new MediaRecorder(stream);
        mr.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data);
        };
        mr.onstop = () => {
          const skip = skipTranscriptionRef.current;
          skipTranscriptionRef.current = false;
          if (!skip && chunksRef.current.length > 0) {
            const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
            transcription(blob);
          }
        };
        mediaRecorderRef.current = mr;
        mr.start();
      }

      transitionTo("LISTENING", "start-listening");
    } catch (error) {
      console.error("Error starting listening:", error);
    }
  }, [ensureMicPipeline, transcription, transitionTo]);

  const stopListening = useCallback((options?: { skipTranscription?: boolean; nextState?: VoiceState }) => {
    if (options?.skipTranscription) {
      skipTranscriptionRef.current = true;
    }
    if (options?.nextState) {
      transitionTo(options.nextState, "stop-listening");
    } else if (voiceStateRef.current === "LISTENING") {
      transitionTo("PROCESSING", "stop-listening");
    }
    setIsUserSpeaking(false);

    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'recording') {
      mr.stop();
    }

    // Note: No longer sending agent_stt_end as we use blob transcription
  }, [transitionTo, setIsUserSpeaking]);

  const resetAudioPipeline = useCallback(async (nextState: VoiceState = "IDLE") => {
    if (resetInProgressRef.current) return;
    resetInProgressRef.current = true;

    transitionTo("RESET", "audio-reset");
    wakeWordEnabledRef.current = true;
    vadEnabledRef.current = true;
    setWakeStatus("AWAITING WAKE WORD");

    stopListening({ skipTranscription: true, nextState: "RESET" });
    ttsEngine.stop();

    await restartMicPipeline();

    if (audioContextRef.current?.state === "suspended") {
      await audioContextRef.current.resume();
    }

    transitionTo(nextState, "audio-reset-complete");
    resetInProgressRef.current = false;
  }, [restartMicPipeline, stopListening, transitionTo]);

  const handleBargeIn = useCallback(async () => {
    if (bargeInRef.current) return;
    bargeInRef.current = true;
    try {
      ttsEngine.stop();
      await brain.handleUserSpeechStart();
      await resetAudioPipeline("LISTENING");
      await startListening();
    } catch (err) {
      console.error("Barge-in failed:", err);
    } finally {
      bargeInRef.current = false;
    }
  }, [resetAudioPipeline, startListening]);

  useEffect(() => {
    let raf = 0;
    let lastActive = 0;
    let wasSpeaking = false;
    const silenceTimeout = 1200; // ms of silence to consider speech ended

    const loop = () => {
      const a = analyserRef.current;
      if (a && vadEnabledRef.current) {
        const buffer = new Uint8Array(a.fftSize);
        a.getByteTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
          const v = (buffer[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / buffer.length);
        const userIsSpeaking = rms > 0.02; // threshold

        if (userIsSpeaking) {
          lastActive = Date.now();
          if (!wasSpeaking) {
            wasSpeaking = true;
            setIsUserSpeaking(true);

            if (voiceStateRef.current === "SPEAKING") {
              void handleBargeIn();
            } else if (voiceStateRef.current === "LISTENING") {
              void brain.handleUserSpeechStart();
            }
          }
        } else if (wasSpeaking && Date.now() - lastActive > silenceTimeout) {
          wasSpeaking = false;
          setIsUserSpeaking(false);
          if (voiceStateRef.current === "LISTENING") {
            stopListening();
          }
        }
      }
      raf = requestAnimationFrame(loop);
    };

    raf = requestAnimationFrame(loop);

    return () => {
      if (raf) cancelAnimationFrame(raf);
    };
  }, [handleBargeIn, stopListening, setIsUserSpeaking]);

  useEffect(() => {
    const callbacks = {
      onStart: () => {
        wakeWordEnabledRef.current = false;
        vadEnabledRef.current = true;
        stopListening({ skipTranscription: true, nextState: "SPEAKING" });
      },
      onEnd: () => {
        if (bargeInRef.current) return;
        void resetAudioPipeline("IDLE");
      },
      onError: (err: unknown) => {
        console.error("[TTS] Error:", err);
        void resetAudioPipeline("IDLE");
      }
    };

    ttsEngine.addCallbacks(callbacks);
    return () => ttsEngine.removeCallbacks(callbacks);
  }, [resetAudioPipeline, stopListening]);

  /* 
   * Brain Integration: Wake Word
   */
  useEffect(() => {
    void initMicPipeline();
    return () => {
      void teardownMicPipeline();
    };
  }, [initMicPipeline, teardownMicPipeline]);

  useEffect(() => {
    const offHot = WakeWordCommunication.onMessage((msg) => {
      if (typeof msg === 'string') {
        try {
          const data = JSON.parse(msg);
          if (data.event && data.event.toLowerCase() === 'wakeword_detected') {
            if (voiceStateRef.current !== "IDLE") return;
            setWakeStatus('WAKE WORD DETECTED');
            brain.handleWakeWordDetected();
            transitionTo("LISTENING", "wake-word");
            startListening();
          }
        } catch (e) { }
      }
    });

    return () => { offHot(); };
  }, [startListening, transitionTo]);

  // Global mic pipeline now managed via initMicPipeline/resetAudioPipeline

  // Keep voice state aligned with backend thinking/idle when no TTS plays.
  const brainState = useBrainState((s) => s.currentState);
  useEffect(() => {
    if (brainState === AssistantState.THINKING && voiceStateRef.current === "LISTENING") {
      transitionTo("PROCESSING", "brain-thinking");
    }
    if (brainState === AssistantState.IDLE && voiceStateRef.current === "PROCESSING") {
      transitionTo("IDLE", "brain-idle");
    }
  }, [brainState, transitionTo]);

  // Listen for real-time events for dialogs
  useEffect(() => {
    const offMsg = AgentCommunication.onMessage((msg) => {
      try {
        const data = JSON.parse(msg);
        if (data.type === 'clarification_required') {
          setClarificationReq({
            task_id: data.task_id,
            question: data.payload.question_text
          });
          // Speak the question
          // (In a fuller version, backend might stream this, but here we can use simple speech synthesis or just let the user read)
        } else if (data.type === 'system_permission_required') {
          setPermissionReq({
            task_id: data.task_id,
            summary: data.payload.command_summary,
            operation: data.payload.exact_operation,
            risk: data.payload.risk_level
          });
        } else if (data.type === 'system_permission_ack' || data.type === 'agent_clarification_ack') {
          if (data.success) {
            setClarificationReq(null);
            setPermissionReq(null);
          }
        }
      } catch (e) { }
    });
    return () => { offMsg(); };
  }, []);

  const handleClarificationResponse = (response: string) => {
    if (clarificationReq) {
      AgentCommunication.sendJSON({
        type: "clarification_response",
        payload: {
          task_id: clarificationReq.task_id,
          text: response
        }
      });
    }
  };

  const handlePermissionResponse = (approved: boolean) => {
    if (permissionReq) {
      AgentCommunication.sendJSON({
        type: "permission_response",
        payload: {
          task_id: permissionReq.task_id,
          approved: approved
        }
      });
    }
  };

  return (
    <div className="relative flex flex-col items-center">
      <div className="relative w-72 h-72 md:w-80 md:h-80">
        <canvas ref={canvasRef} className="w-full h-full" />
        <motion.div className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}>
          <JarvisButton
            variant={isListening ? "orange" : "primary"}
            size="xl"
            className={`pointer-events-auto rounded-full w-20 h-20 ${voiceState === "SPEAKING" ? 'ring-4 ring-primary/40 animate-pulse' : ''}`}
            onClick={() => {
              if (isListening) {
                stopListening();
              } else {
                void startListening();
              }
            }}
            disabled={isTranscribing}
          >
            {isListening ? <MicOff size={28} /> : <Mic size={28} />}
          </JarvisButton>
        </motion.div>
      </div>

      <motion.div
        className="mt-4 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <ListeningAnimation isTranscribing={isTranscribing} voiceState={voiceState} />
      </motion.div>

      {/* Clarification Dialog */}
      {clarificationReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-jarvis-dark border border-primary/40 p-6 rounded-xl max-w-md w-full shadow-2xl glow-border"
          >
            <h3 className="text-xl font-orbitron text-primary mb-4">CLARIFICATION REQUIRED</h3>
            <p className="text-foreground/90 mb-6">{clarificationReq.question}</p>
            <div className="flex flex-col gap-3">
              <div className="p-2 border border-dashed border-primary/20 rounded text-xs text-muted-foreground text-center">
                Please respond via voice or type below
              </div>
              <input
                type="text"
                className="bg-jarvis-black border border-primary/20 p-2 rounded text-sm focus:border-primary outline-none"
                placeholder="Your response..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleClarificationResponse(e.currentTarget.value);
                }}
              />
              <JarvisButton variant="primary" onClick={() => {
                const input = document.querySelector('input') as HTMLInputElement;
                handleClarificationResponse(input.value);
              }}>
                SUBMIT RESPONSE
              </JarvisButton>
            </div>
          </motion.div>
        </div>
      )}

      {/* Permission Dialog */}
      {permissionReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-jarvis-dark border border-orange-500/40 p-6 rounded-xl max-w-md w-full shadow-2xl glow-border"
          >
            <h3 className="text-xl font-orbitron text-orange-500 mb-2">SECURITY PERMISSION</h3>
            <div className="mb-4 text-sm">
              <div className="text-muted-foreground mb-1">Action Summary:</div>
              <div className="font-semibold">{permissionReq.summary}</div>
            </div>
            <div className="mb-4 text-xs bg-black/40 p-2 rounded font-mono break-all">
              {permissionReq.operation}
            </div>
            <div className={`mb-6 text-xs font-bold ${permissionReq.risk === 'high' ? 'text-red-500' : 'text-orange-400'}`}>
              RISK LEVEL: {permissionReq.risk.toUpperCase()}
            </div>
            <div className="flex gap-4">
              <JarvisButton variant="orange" className="flex-1" onClick={() => handlePermissionResponse(true)}>
                APPROVE
              </JarvisButton>
              <JarvisButton variant="danger" className="flex-1" onClick={() => handlePermissionResponse(false)}>
                DENY
              </JarvisButton>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};
