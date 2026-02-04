from openai import AsyncOpenAI
from typing import Optional, List, Dict, Any
import os
import json

class LLMClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance.client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE") 
            )
        return cls._instance

    async def get_response(self, messages: List[Dict[str, str]], model: str = "gpt-4o", temperature: float = 0.7, json_mode: bool = False) -> str:
        """
        Get a simple text response from the LLM.
        """
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""

    async def classify_intent(self, query: str, context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Specialized method for intent classification to ensure consistent JSON structure.
        """
        system_prompt = """
        You are the Intent Classifier for Jarvis.
        Analyze the user's input and classify it into one of the following categories:
        - CALENDAR: Scheduling, checking events, reminders.
        - TASK: To-do list, shopping list, tracking items.
        - NOTE: Taking notes, recording ideas.
        - BRIEFING: Daily summary, agenda, morning update, what's up today.
        - SMART_HOME: Controlling lights, thermostat, devices.
        - QUERY: General knowledge, weather, news, questions requiring search.
        - SYSTEM: Volume, app control, system status.
        
        Extract relevant entities (dates, times, device names, content).
        
        Return JSON format:
        {
            "intent": "CATEGORY",
            "entities": { ... },
            "confidence": 0.0-1.0,
            "original_query": "..."
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        response_text = await self.get_response(messages, temperature=0.0, json_mode=True)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"intent": "QUERY", "entities": {}, "confidence": 0.0, "original_query": query}

# Global instance
llm_client = LLMClient()
