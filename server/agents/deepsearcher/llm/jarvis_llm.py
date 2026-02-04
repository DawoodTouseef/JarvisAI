import os
import json
import requests
import logging
from typing import Dict, List, Optional

from ..llm.base import BaseLLM, ChatResponse

logger = logging.getLogger(__name__)

class JarvisLLM(BaseLLM):
    """
    Jarvis Server LLM implementation.

    This class provides an interface to interact with language models
    through the Jarvis Server API.
    """

    def __init__(self, model: str = "qwen3:latest", **kwargs):
        """
        Initialize a Jarvis language model client.

        Args:
            model (str, optional): The model identifier to use. Defaults to "qwen3:latest".
            **kwargs: Additional keyword arguments.
                - api_key/auth_token: Authentication token.
                - base_url/server_url: Jarvis Server base URL.
        """
        self.model = model
        
        # Get base URL
        self.base_url = kwargs.get("base_url") or kwargs.get("server_url") or os.getenv("JARVIS_SERVER_URL") or "http://localhost:8080"
        self.base_url = self.base_url.rstrip("/")
        
        # Get auth token
        self.auth_token = kwargs.get("api_key") or kwargs.get("auth_token") or kwargs.get("api_token") or os.getenv("JARVIS_AUTH_TOKEN")
        
        self.timeout = kwargs.get("timeout", 60)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def chat(self, messages: List[Dict]) -> ChatResponse:
        """
        Send a chat message to the Jarvis Server and get a response.

        Args:
            messages (List[Dict]): A list of message dictionaries.

        Returns:
            ChatResponse: An object containing the model's response and token usage information.
        """
        url = f"{self.base_url}/api/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            total_tokens = data.get("usage", {}).get("total_tokens", 0)
            
            return ChatResponse(
                content=content,
                total_tokens=total_tokens,
            )
        except Exception as e:
            logger.error(f"Jarvis LLM request failed: {e}")
            raise RuntimeError(f"Jarvis LLM request failed: {e}")
