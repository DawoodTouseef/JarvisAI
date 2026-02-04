class STTService:
    def __init__(self):
        pass

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes to text.
        For Phase 1, we rely on the frontend sending text,
        but this is where server-side Whisper or Azure STT would go.
        """
        """
        Transcribe audio bytes to text.
        For Phase 1, we rely on the frontend sending text,
        but this is where server-side Whisper or Azure STT would go.
        """
        # Simulate STT
        return "Audio received and stored."

stt_service = STTService()
