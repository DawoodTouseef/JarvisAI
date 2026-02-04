import pyttsx3
import os
import base64
import tempfile
from abc import ABC, abstractmethod

class TTSProvider(ABC):
    @abstractmethod
    async def speak(self, text: str) -> bytes:
        """Convert text to audio bytes (mp3/wav)"""
        pass

class Pyttsx3Provider(TTSProvider):
    def __init__(self):
        self.engine = pyttsx3.init()
        # Set default properties
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

    async def speak(self, text: str) -> bytes:
        # pyttsx3 saves to file, then we read bytes
        temp_file = os.path.join(tempfile.gettempdir(), "jarvis_tts_temp.wav")
        self.engine.save_to_file(text, temp_file)
        self.engine.runAndWait()
        
        with open(temp_file, "rb") as f:
            audio_data = f.read()
        
        # Cleanup
        try:
            os.remove(temp_file)
        except:
            pass
            
        return audio_data

class AzureTTSProvider(TTSProvider):
    def __init__(self):
        self.key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION")
        
    async def speak(self, text: str) -> bytes:
        if not self.key or not self.region:
            print("Azure TTS credentials not found, falling back.")
            raise ValueError("Azure credentials missing")
        # Implementation for Azure would go here using azure-cognitiveservices-speech
        pass

class TTSService:
    def __init__(self, provider_type="offline"):
        if provider_type == "azure":
            self.provider = AzureTTSProvider()
        else:
            self.provider = Pyttsx3Provider()
    
    async def generate_audio(self, text: str) -> bytes:
        """Generate audio from text and return bytes"""
        try:
            return await self.provider.speak(text)
        except Exception as e:
            print(f"TTS Error: {e}")
            # Fallback to offline if primary fails
            if not isinstance(self.provider, Pyttsx3Provider):
                print("Falling back to offline TTS")
                fallback = Pyttsx3Provider()
                return await fallback.speak(text)
            return b""
    
    async def generate_audio_base64(self, text: str) -> str:
        audio_bytes = await self.generate_audio(text)
        return base64.b64encode(audio_bytes).decode('utf-8')

# Global instance
tts_service = TTSService(provider_type=os.getenv("TTS_PROVIDER", "offline"))
