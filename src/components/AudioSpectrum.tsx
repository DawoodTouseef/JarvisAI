import { useRef, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { toast } from "sonner";
import { useTranscriptionStore } from "@/stores/transcription";
import { Communication } from "@/lib/client_websocket";
import { useSpeakingStore } from "@/stores/speaking";
import { WakeWordCommunication } from "@/lib/client_websocket";




const TranscriptionAnimation = ({ text }: { text: string }) => {
  if (!text) return <p className="text-xs text-muted-foreground mt-2"></p>;
  const chars = text.split('  ');

  const container = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.02 } },
  } as const;

  const child = {
    hidden: { opacity: 0, y: 6 },
    visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 400, damping: 24 } },
  } as const;

  return (
    <motion.p
      className="mt-2 text-center text-sm font-rajdhani text-primary glow-text shimmer-wrap"
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
};
const ListeningAnimation = ({ isTranscribing, isListening }: { isTranscribing: boolean; isListening: boolean; }) => {
  let  isSpeaking = useSpeakingStore((s) => s.isSpeaking);
  const text = isTranscribing ? "TRANSCRIBING..." : isSpeaking ? "SPEAKING..." : isListening ? "LISTENING..." : "AWAITING VOICE COMMAND";
        
  const chars = text.split('  ');

  const container = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.02 } },
  } as const;

  const child = {
    hidden: { opacity: 0, y: 6 },
    visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 400, damping: 24 } },
  } as const;
  
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
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [isListening, setIsListening] = useState(false);
  const chunksRef = useRef<Blob[]>([]);
  const url = localStorage.getItem('jarvis:selectedServer') || '';
  // hotword scanning state
  const hotwordStreamRef = useRef<MediaStream | null>(null);
  const hotwordCtxRef = useRef<AudioContext | null>(null);
  const hotwordNodeRef = useRef<ScriptProcessorNode | null>(null);
  const hotwordListeningRef = useRef<boolean>(false);
  const [wakeStatus, setWakeStatus] = useState<string>("AWAITING WAKE WORD");
  // Global transcription available throughout the app
  const transcriptions = useTranscriptionStore((s) => s.text);
  const setTranscription = useTranscriptionStore((s) => s.setText);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [lastSocketMessage, setLastSocketMessage] = useState<string>('');
  const isSpeaking = useSpeakingStore((s) => s.isSpeaking);
  const setIsSpeaking = useSpeakingStore((s) => s.setText);
    const drawSpectrum = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.6;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background glow
    const bgGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius * 1.5);
    bgGradient.addColorStop(0, "hsla(185, 100%, 50%, 0.05)");
    bgGradient.addColorStop(1, "transparent");
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const bars = 64;
    const dataArray = new Uint8Array(bars);

    if (analyser && isListening) {
      const tempArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(tempArray);
      for (let i = 0; i < bars && i < tempArray.length; i++) {
        dataArray[i] = tempArray[i];
      }
    } else {
      // Idle animation
      const time = Date.now() / 1000;
      for (let i = 0; i < bars; i++) {
        dataArray[i] = 30 + Math.sin(time * 2 + i * 0.3) * 20 + Math.sin(time * 0.5 + i * 0.1) * 10;
      }
    }

    // Draw circular spectrum
    for (let i = 0; i < bars; i++) {
      const angle = (i / bars) * Math.PI * 2 - Math.PI / 2;
      const value = dataArray[i] || 0;
      const barHeight = (value / 255) * radius * 0.8 + 10;

      const innerRadius = radius * 0.4;
      const x1 = centerX + Math.cos(angle) * innerRadius;
      const y1 = centerY + Math.sin(angle) * innerRadius;
      const x2 = centerX + Math.cos(angle) * (innerRadius + barHeight);
      const y2 = centerY + Math.sin(angle) * (innerRadius + barHeight);

      // Gradient for bars
      const gradient = ctx.createLinearGradient(x1, y1, x2, y2);
      gradient.addColorStop(0, "hsla(185, 100%, 50%, 0.6)");
      gradient.addColorStop(0.5, "hsla(185, 100%, 60%, 0.8)");
      gradient.addColorStop(1, "hsla(210, 100%, 60%, 0.9)");

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.stroke();

      // Glow effect
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = `hsla(185, 100%, 50%, ${0.2 + (value / 255) * 0.3})`;
      ctx.lineWidth = 8;
      ctx.lineCap = "round";
      ctx.stroke();
    }

    // Draw inner circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.35, 0, Math.PI * 2);
    ctx.strokeStyle = "hsla(185, 100%, 50%, 0.3)";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw pulsing center
    const pulseScale = 1 + Math.sin(Date.now() / 500) * (isSpeaking ? 0.25 : 0.1);
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.15 * pulseScale, 0, Math.PI * 2);
    const centerGradient = ctx.createRadialGradient(
      centerX, centerY, 0,
      centerX, centerY, radius * 0.15 * pulseScale
    );
    centerGradient.addColorStop(0, "hsla(185, 100%, 60%, 0.8)");
    centerGradient.addColorStop(1, "hsla(185, 100%, 50%, 0.2)");
    ctx.fillStyle = centerGradient;
    ctx.fill();

    animationRef.current = requestAnimationFrame(drawSpectrum);
  }, [analyser, isListening]);

  useEffect(() => {
    let raf = 0;
    let lastActive = 0;
    const silenceTimeout = 700; // ms of silence to consider speech ended

    const startIfNeeded = () => {
      const mr = mediaRecorderRef.current;
      if (mr && mr.state === 'inactive') {
        try {
          mr.start();
        } catch (e) {
          console.warn('MediaRecorder start failed', e);
        }
      }
    };

    const stopIfNeeded = () => {
      const mr = mediaRecorderRef.current;
      if (mr && mr.state === 'recording') {
        try {
          mr.stop();
        } catch (e) {
          console.warn('MediaRecorder stop failed', e);
        }
      }
    };

    const loop = async () => {
      const a = analyser;
      if (a) {
        const buffer = new Uint8Array(a.fftSize);
        a.getByteTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
          const v = (buffer[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / buffer.length);
        const speaking = rms > 0.02; // threshold - tweak if needed
        if (speaking) {
          lastActive = Date.now();
          if (!isSpeaking) {
            setIsSpeaking(true);
            startIfNeeded();
            
          }
        } else {
          if (isSpeaking && Date.now() - lastActive > silenceTimeout) {
            setIsSpeaking(false);
            stopIfNeeded();
            // Speech ended: stop recording and let onstop handler process/upload the blob
          }
        }
      }
      raf = requestAnimationFrame(loop);
    };

    if (isListening && analyser) {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      if (raf) cancelAnimationFrame(raf);
    };
  }, [isListening, analyser, isSpeaking]);

  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const analyserNode = context.createAnalyser();
      analyserNode.fftSize = 256;
      source.connect(analyserNode);

      // Prepare media recorder to capture audio for transcription
      chunksRef.current = [];
      if (typeof MediaRecorder !== 'undefined') {
        try {
          const options = { mimeType: 'audio/webm;codecs=opus' };
          const mr = new MediaRecorder(stream, options);
          mr.ondataavailable = (e: BlobEvent) => {
            if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
          };
          mr.onstop = async () => {
            const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
            chunksRef.current = [];
            if (audioBlob.size > 0) {
              await transcription(audioBlob);
            }
            mediaRecorderRef.current = null;
          };
          mediaRecorderRef.current = mr;
          // Recorder will be started/stopped automatically by VAD when speech begins/ends.
        } catch (err) {
          console.warn('MediaRecorder not supported or failed to start', err);
        }
      }

      setAudioContext(context);
      setAnalyser(analyserNode);
      setIsListening(true);
      setIsTranscribing(false);

    } catch (error) {
      console.error("Error accessing microphone:", error);
    }
  }, []);

  const transcription = async (audioBlob: Blob) => {
    if (!url) {
      toast.error('No server selected for transcription. Please select a server on the Services page.');
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
        headers:{
          "Authorization": `Bearer ${localStorage.getItem("jarvis:token") || ''}`
        }
      });
      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(text || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setTranscription([...transcriptions,data.text]);
      handleTranscription(data.text);
      
      stopListening();
    } catch (error) {
      console.error("Error during transcription:", error);
    } finally {
      setIsTranscribing(false);
    }
  };
  const handleTranscription = (text: string) => {
    // Use the shared Communication client to send transcription to backend websocket
    try {
      Communication.sendMessage(text);
    } catch (err) {
      console.error('Failed to send transcription over websocket', err);

    }
  };
  const stopListening = () => {
    // Stop the media recorder to finalize the audio blob and trigger transcription
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        // mark as transcribing immediately so UI reflects upload in progress
        setIsTranscribing(true);
        mediaRecorderRef.current.stop();
        setIsSpeaking(false);
      } catch (err) {
        console.warn('Error stopping MediaRecorder', err);
      }
    }
    if (audioContext) {
      audioContext.close();
      setAudioContext(null);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setAnalyser(null);
    setIsListening(false);
  }; 

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      const container = canvas.parentElement;
      if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
      }
    };
    resize();
    window.addEventListener("resize", resize);

    drawSpectrum();

    return () => {
      window.removeEventListener("resize", resize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [drawSpectrum]);

  useEffect(() => {
    const offHot = WakeWordCommunication.onMessage((msg) => {
      if (typeof msg === 'string') {
        try {
          const data = JSON.parse(msg);
          if (data.event && data.event.toLowerCase() === 'wakeword_detected') {
            setWakeStatus('WAKE WORD DETECTED');
            startListening();
          }
        } catch (e) {
          console.error('Failed to parse hotword message:', e);
        }
      }
    });
    return () => { offHot(); };
  }, [startListening]);


  // Subscribe to general websocket messages
  useEffect(() => {
    const off = Communication.onMessage((msg) => {
      setLastSocketMessage(msg);
    });
    return () => { off(); };
  }, []);

  // Hotword VAD + streaming
  useEffect(() => {
    let speaking = false;
    let lastActive = 0;
    const hangoverMs = 300;
    const rmsStart = 0.015;
    const rmsContinue = 0.01;

    const init = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        hotwordStreamRef.current = stream;
        const ctx = new AudioContext();
        hotwordCtxRef.current = ctx;
        const src = ctx.createMediaStreamSource(stream);
        const node = ctx.createScriptProcessor(4096, 1, 1);
        hotwordNodeRef.current = node;
        const inputBuf: Float32Array[] = [];

        const to16k = (pcm: Float32Array, inRate: number, outRate = 16000) => {
          if (inRate === outRate) return pcm;
          const ratio = inRate / outRate;
          const newLen = Math.round(pcm.length / ratio);
          const res = new Float32Array(newLen);
          let idx = 0;
          let pos = 0;
          while (idx < newLen) {
            const nextPos = Math.min(pcm.length, Math.round((idx + 1) * ratio));
            let sum = 0;
            let count = 0;
            while (pos < nextPos) { sum += pcm[pos++]; count++; }
            res[idx++] = count ? sum / count : 0;
          }
          return res;
        };

        const floatTo16BitPCM = (input: Float32Array) => {
          const out = new Int16Array(input.length);
          for (let i = 0; i < input.length; i++) {
            let s = Math.max(-1, Math.min(1, input[i]));
            out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          return out;
        };

        const wavHeader = (numSamples: number, sampleRate = 16000, numChannels = 1) => {
          const blockAlign = numChannels * 2;
          const byteRate = sampleRate * blockAlign;
          const dataSize = numSamples * 2;
          const buffer = new ArrayBuffer(44 + dataSize);
          const view = new DataView(buffer);

          const writeStr = (off: number, s: string) => {
            for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
          };

          writeStr(0, 'RIFF');
          view.setUint32(4, 36 + dataSize, true);
          writeStr(8, 'WAVE');
          writeStr(12, 'fmt ');
          view.setUint32(16, 16, true);
          view.setUint16(20, 1, true);
          view.setUint16(22, numChannels, true);
          view.setUint32(24, sampleRate, true);
          view.setUint32(28, byteRate, true);
          view.setUint16(32, blockAlign, true);
          view.setUint16(34, 16, true);
          writeStr(36, 'data');
          view.setUint32(40, dataSize, true);
          return view;
        };

        const flushAndSend = () => {
          const merged = concatFloat32(inputBuf);
          inputBuf.length = 0;
          if (merged.length === 0) return;
          const pcm16 = floatTo16BitPCM(merged);
          const header = wavHeader(pcm16.length);
          const wav = new Uint8Array(header.buffer.byteLength);
          for (let i = 0; i < 44; i++) wav[i] = header.getUint8(i);
          const body = new Uint8Array(pcm16.buffer);
          const final = new Uint8Array(44 + body.length);
          final.set(wav, 0);
          final.set(body, 44);
          WakeWordCommunication.sendBytes(final.buffer);
        };

        const concatFloat32 = (chunks: Float32Array[]) => {
          let total = 0;
          for (const c of chunks) total += c.length;
          const res = new Float32Array(total);
          let off = 0;
          for (const c of chunks) { res.set(c, off); off += c.length; }
          return res;
        };

        node.onaudioprocess = (e) => {
          if (!hotwordListeningRef.current) return;
          const ch = e.inputBuffer.getChannelData(0);
          const down = to16k(ch, ctx.sampleRate, 16000);
          let sum = 0;
          for (let i = 0; i < down.length; i++) { const v = down[i]; sum += v * v; }
          const rms = Math.sqrt(sum / down.length);
          const now = performance.now();

          if (!speaking) {
            if (rms > rmsStart) {
              speaking = true;
              lastActive = now;
              inputBuf.push(down.slice());
            }
          } else {
            if (rms > rmsContinue) {
              lastActive = now;
              inputBuf.push(down.slice());
            } else {
              if (now - lastActive > hangoverMs) {
                speaking = false;
                flushAndSend();
              } else {
                inputBuf.push(down.slice());
              }
            }
          }
        };

        src.connect(node);
        node.connect(ctx.destination);
        hotwordListeningRef.current = true;
        setWakeStatus('AWAITING WAKE WORD');
      } catch (e) {
        console.error('Hotword init failed', e);
      }
    };

    init();
    return () => {
      hotwordListeningRef.current = false;
      if (hotwordNodeRef.current) {
        try { hotwordNodeRef.current.disconnect(); } catch {}
        hotwordNodeRef.current = null;
      }
      if (hotwordCtxRef.current) {
        try { hotwordCtxRef.current.close(); } catch {}
        hotwordCtxRef.current = null;
      }
      if (hotwordStreamRef.current) {
        try { hotwordStreamRef.current.getTracks().forEach(t => t.stop()); } catch {}
        hotwordStreamRef.current = null;
      }
    };
  }, []);

  return (
    <div className="relative flex flex-col items-center">
      <div className="relative w-72 h-72 md:w-80 md:h-80">
        <canvas ref={canvasRef} className="w-full h-full" />
        <motion.div className="absolute inset-0 flex items-center justify-center pointer-events-none"
          initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}>
          <JarvisButton
            variant={isListening ? "orange" : "primary"}
            size="xl"
            className={`pointer-events-auto rounded-full w-20 h-20 ${isSpeaking ? 'ring-4 ring-primary/40 animate-pulse' : ''}`}
            onClick={isListening ? stopListening : startListening}
            disabled={isTranscribing}
          >
            {isListening ? <MicOff size={28} /> : <Mic size={28} />}
          </JarvisButton>
        </motion.div>
      </div>

      {/* Status text */}
      <motion.div
        className="mt-4 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <ListeningAnimation isTranscribing={isTranscribing} isListening={isListening} />
        {transcription.length> 0 && (
        <TranscriptionAnimation text={transcriptions.at(-1).text[0]} />
        )}
      </motion.div>
    </div>
  );
};
