import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "./ui/GlassPanel";
import { useVideoStore } from "../stores/video";

const Video = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const [error, setError] = useState<string | null>(null);
  const setVideoStream = useVideoStore((s) => s.setVideoStream);

  useEffect(() => {
    let streamToUse: MediaStream | null = null;
    
    const startCamera = async () => {
      try {
        setError(null);
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: true,
        });
        streamToUse = mediaStream;
        setStream(mediaStream);
        
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          
          // Ensure the video plays properly
          videoRef.current.muted = true;
          videoRef.current.autoplay = true;
          videoRef.current.playsInline = true;
          
          // Wait for video to load metadata to ensure proper playback
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(e => console.error("Error playing video:", e));
          };
        }
        
        // Store the stream in zustand for other components to use
        setVideoStream(mediaStream);
      } catch (err) {
        console.error("Error accessing camera:", err);
        setError("Failed to access camera. Please check permissions.");
      }
    };

    startCamera();

    // Cleanup function
    return () => {
      if (streamToUse) {
        const tracks = streamToUse.getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, [setVideoStream]);

  return (
    <GlassPanel className="p-4">
      <div className="relative aspect-video bg-gray-800 rounded-lg overflow-hidden">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-500 p-4">
            {error}
          </div>
        )}
        <div className="w-full h-full">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        </div>
      </div>
    </GlassPanel>
  );
};

export default Video;
