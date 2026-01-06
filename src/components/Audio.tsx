// client/lib/audio.ts

import RecordRTC, { StereoAudioRecorder } from 'recordrtc';

export class AudioRecorder {
  private recorder: RecordRTC | null = null;
  private stream: MediaStream | null = null;

  async initialize(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });
    } catch (error) {
      console.error('Microphone access denied:', error);
      throw new Error('Microphone access required');
    }
  }

  startRecording(): void {
    if (!this.stream) {
      throw new Error('Audio stream not initialized');
    }

    this.recorder = new RecordRTC(this.stream, {
      type: 'audio',
      mimeType: 'audio/webm',
      recorderType: StereoAudioRecorder,
      numberOfAudioChannels: 1,
      desiredSampRate: 16000,
    });

    this.recorder.startRecording();
    console.log('🎤 Recording started');
  }

  async stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.recorder) {
        reject(new Error('No active recording'));
        return;
      }

      this.recorder.stopRecording(() => {
        const blob = this.recorder!.getBlob();
        console.log('🛑 Recording stopped');
        resolve(blob);
      });
    });
  }

  getStream(): MediaStream | null {
    return this.stream;
  }

  cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.recorder = null;
  }
}