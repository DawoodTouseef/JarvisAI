import { useEffect, useRef } from "react";
import { AgentCommunication } from "@/lib/client_websocket";
import { useVideoStore } from "@/stores/video";

interface CameraVisionSenderProps {
  enabled: boolean;
}

export const CameraVisionSender = ({ enabled }: CameraVisionSenderProps) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const intervalRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const createdStreamRef = useRef(false);
  const { videostream, setVideoStream, clear } = useVideoStore();

  useEffect(() => {
    if (!enabled) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (streamRef.current && createdStreamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        createdStreamRef.current = false;
        clear();
      }
      AgentCommunication.sendJSON({
        type: "vision_input",
        payload: { camera_enabled: false, has_frame: false },
      });
      return;
    }

    const start = async () => {
      let stream = videostream;
      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        setVideoStream(stream);
        createdStreamRef.current = true;
      }
      streamRef.current = stream;

      if (!videoRef.current) {
        videoRef.current = document.createElement("video");
      }
      videoRef.current.srcObject = stream;
      videoRef.current.muted = true;
      await videoRef.current.play().catch(() => null);

      if (!intervalRef.current) {
        intervalRef.current = window.setInterval(() => {
          if (!videoRef.current) return;
          const canvas = document.createElement("canvas");
          canvas.width = videoRef.current.videoWidth || 1280;
          canvas.height = videoRef.current.videoHeight || 720;
          const ctx = canvas.getContext("2d");
          if (!ctx) return;
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => {
            if (!blob) return;
            AgentCommunication.sendJSON({
              type: "vision_input",
              payload: { camera_enabled: true, has_frame: true, timestamp: Date.now() },
            });
            AgentCommunication.sendBytes(blob);
          }, "image/jpeg", 0.7);
        }, 1500);
      }
    };

    start().catch((e) => {
      console.error("CameraVisionSender error:", e);
    });

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, videostream, setVideoStream, clear]);

  return null;
};
