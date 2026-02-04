"""
ChatAIServer - LangChain-compatible BaseChatModel for Jarvis Server

This module provides a LangChain-compatible chat model that connects to
the jarvis-server API for unified access to multiple LLM providers.

Usage:
    from server.services.chat_ai_server import ChatAIServer
    
    model = ChatAIServer(
        model="gpt-4o",
        server_url="http://localhost:8080",
        auth_token="your-token"
    )
    
    response = model.invoke([HumanMessage(content="Hello!")])
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterator, List, Optional, AsyncIterator,TypeAlias

from langchain_core.tools import BaseTool
import aiohttp
import requests
from pydantic import Field,BaseModel
from typing import TypeVar

from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessageChunk,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from langchain_openai.chat_models.base import _convert_to_openai_response_format
from typing import Sequence, Callable, cast





import json
import logging
import os

from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Sequence,
)

from typing import (
    Any,

    cast,
)
from urllib.parse import urlparse


from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import (
    LanguageModelInput,

)
from langchain_core.language_models.chat_models import (
    BaseChatModel,

)
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,

    HumanMessage,

    SystemMessage,

    ToolMessage,

)



from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import (
    Runnable,
)

from langchain_core.utils.function_calling import (
    convert_to_openai_tool,
)

from pydantic import (

    Field,

)



logger = logging.getLogger(__name__)

_BM = TypeVar("_BM", bound=BaseModel)
_DictOrPydanticClass: TypeAlias = dict[str, Any] | type[_BM] | type

@dataclass
class ChatCompletionRequest:
    """Helper class for building API requests."""
    
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format."""
        result = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": self.stream,
        }
        
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.stop:
            result["stop"] = self.stop
        if self.presence_penalty != 0.0:
            result["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty != 0.0:
            result["frequency_penalty"] = self.frequency_penalty
            
        return result


class ChatAIServer(BaseChatModel):
    """
    LangChain-compatible chat model for Jarvis Server.
    
    Connects to the jarvis-server's OpenAI-compatible API endpoint
    to provide unified access to multiple LLM providers.
    
    Attributes:
        model: The model identifier (e.g., "gpt-4o", "claude-3-opus")
        server_url: The jarvis-server URL (default from JARVIS_SERVER_URL env)
        auth_token: Authentication token (default from JARVIS_AUTH_TOKEN env)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum response tokens (None for model default)
        top_p: Nucleus sampling parameter
        stop: Optional list of stop sequences
        streaming: Whether to enable streaming responses
        timeout: Request timeout in seconds
        presence_penalty: Penalty for token presence
        frequency_penalty: Penalty for token frequency
    
    Example:
        >>> from langchain_core.messages import HumanMessage, SystemMessage
        >>> model = ChatAIServer(
        ...     model="gpt-4o",
        ...     server_url="http://localhost:8080",
        ...     temperature=0.7
        ... )
        >>> response = model.invoke([
        ...     SystemMessage(content="You are a helpful assistant."),
        ...     HumanMessage(content="What is AI?")
        ... ])
        >>> print(response.content)
    """
    
    # Configuration fields
    model: str = Field(default="qwen3:latest", description="Model identifier")
    server_url: str = Field(
        default_factory=lambda: os.getenv("JARVIS_SERVER_URL", "http://localhost:8080"),
        description="Jarvis server URL"
    )
    auth_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("JARVIS_AUTH_TOKEN"),
        description="Authentication token"
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("JARVIS_API_KEY"),
        description="API key"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Maximum response tokens")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    streaming: bool = Field(default=False, description="Enable streaming responses")
    timeout: int = Field(default=300, description="Request timeout in seconds")
    presence_penalty: float = Field(default=0.0, description="Presence penalty")
    frequency_penalty: float = Field(default=0.0, description="Frequency penalty")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "chat-ai-server"
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for caching."""
        return {
            "model": self.model,
            "server_url": self.server_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }
    
    def _convert_messages_to_api_format(
        self, messages: List[BaseMessage]
    ) -> List[Dict[str, str]]:
        """
        Convert LangChain message objects to API format.
        
        Args:
            messages: List of LangChain BaseMessage objects
            
        Returns:
            List of message dictionaries in API format
        """
        api_messages = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                api_messages.append({
                    "role": "system",
                    "content": message.content
                })
            elif isinstance(message, HumanMessage):
                api_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif isinstance(message, AIMessage):
                msg_dict = {
                    "role": "assistant",
                    "content": message.content
                }
                # Handle tool calls if present
                if message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"])
                            }
                        }
                        for tc in message.tool_calls
                    ]
                api_messages.append(msg_dict)
            elif isinstance(message, ToolMessage):
                api_messages.append({
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.tool_call_id
                })
            else:
                # Generic fallback
                api_messages.append({
                    "role": "user",
                    "content": str(message.content)
                })
                
        return api_messages
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _get_api_url(self) -> str:
        """Get the chat completions API URL.
        
        Uses the generic endpoint which handles payload conversion (OpenAI -> Ollama)
        and routing to the correct backend.
        """
        base_url = self.server_url.rstrip("/")
        return f"{base_url}/api/v1/chat/completions"
    
    def _parse_response(self, response_data: Any) -> ChatResult:
        """
        Parse API response into ChatResult.
        
        Args:
            response_data: Raw API response (dict, None, or other)
            
        Returns:
            ChatResult containing the generated message
            
        Raises:
            ValueError: If response format is invalid
        """
        # Handle None or non-dict responses
        if response_data is None:
            raise ValueError("API returned None response - check server logs for details")
        
        if not isinstance(response_data, dict):
            raise ValueError(f"API returned unexpected type: {type(response_data).__name__}, value: {response_data}")
        
        if "error" in response_data:
            raise ValueError(f"API Error: {response_data['error']}")
        
        choices = response_data.get("choices", [])
        if not choices:
            raise ValueError(f"No choices in API response. Full response: {response_data}")
        
        generations = []
        for choice in choices:
            message_data = choice.get("message", {})
            content = message_data.get("content", "")
            
            # Create AIMessage with optional tool_calls
            ai_message_kwargs = {"content": content}
            
            if "tool_calls" in message_data and message_data["tool_calls"]:
                tool_calls = []
                for tc in message_data["tool_calls"]:
                    tool_calls.append({
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "args": json.loads(tc.get("function", {}).get("arguments", "{}"))
                    })
                ai_message_kwargs["tool_calls"] = tool_calls
            
            ai_message = AIMessage(**ai_message_kwargs)
            
            generation = ChatGeneration(
                message=ai_message,
                generation_info={
                    "finish_reason": choice.get("finish_reason"),
                    "index": choice.get("index", 0),
                }
            )
            generations.append(generation)
        
        # Extract metadata
        llm_output = {
            "model": response_data.get("model", self.model),
            "usage": response_data.get("usage", {}),
        }
        
        return ChatResult(generations=generations, llm_output=llm_output)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a chat completion synchronously.
        
        Args:
            messages: List of LangChain messages
            stop: Optional stop sequences (overrides instance setting)
            run_manager: Callback manager for the run
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            ChatResult containing the generated response
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
        """
        api_messages = self._convert_messages_to_api_format(messages)
        
        # Build request
        request = ChatCompletionRequest(
            model=self.model,
            messages=api_messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
            stop=stop or self.stop,
            stream=False,
            presence_penalty=kwargs.get("presence_penalty", self.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
        )
        
        try:
            url = self._get_api_url()
            headers = self._get_headers()
            payload = request.to_dict()
            
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            
            logger.debug(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            response_data = response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise RuntimeError(f"ChatAIServer API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            raise RuntimeError(f"Failed to parse API response: {e}")
        
        return self._parse_response(response_data)
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a chat completion asynchronously.
        
        Args:
            messages: List of LangChain messages
            stop: Optional stop sequences (overrides instance setting)
            run_manager: Async callback manager for the run
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            ChatResult containing the generated response
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
        """
        api_messages = self._convert_messages_to_api_format(messages)
        
        # Build request
        request = ChatCompletionRequest(
            model=self.model,
            messages=api_messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
            stop=stop or self.stop,
            stream=False,
            presence_penalty=kwargs.get("presence_penalty", self.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
        )
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self._get_api_url(),
                    headers=self._get_headers(),
                    json=request.to_dict(),
                ) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Async API request failed: {e}")
            raise RuntimeError(f"ChatAIServer async API request failed: {e}")
        return self._parse_response(response_data)
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """
        Stream a chat completion synchronously.
        
        Args:
            messages: List of LangChain messages
            stop: Optional stop sequences
            run_manager: Callback manager for the run
            **kwargs: Additional parameters
            
        Yields:
            ChatGenerationChunk for each streamed token
        """
        api_messages = self._convert_messages_to_api_format(messages)
        
        request = ChatCompletionRequest(
            model=self.model,
            messages=api_messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
            stop=stop or self.stop,
            stream=True,
            presence_penalty=kwargs.get("presence_penalty", self.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
        )
        
        try:
            with requests.post(
                self._get_api_url(),
                headers=self._get_headers(),
                json=request.to_dict(),
                timeout=self.timeout,
                stream=True,
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data)
                                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunk = ChatGenerationChunk(
                                        message=AIMessageChunk(content=content)
                                    )
                                    if run_manager:
                                        run_manager.on_llm_new_token(content)
                                    yield chunk
                            except json.JSONDecodeError:
                                continue
                                
        except requests.exceptions.RequestException as e:
            logger.error(f"Streaming request failed: {e}")
            raise RuntimeError(f"ChatAIServer streaming request failed: {e}")
    
    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """
        Stream a chat completion asynchronously.
        
        Args:
            messages: List of LangChain messages
            stop: Optional stop sequences
            run_manager: Async callback manager for the run
            **kwargs: Additional parameters
            
        Yields:
            ChatGenerationChunk for each streamed token
        """
        api_messages = self._convert_messages_to_api_format(messages)
        
        request = ChatCompletionRequest(
            model=self.model,
            messages=api_messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            top_p=kwargs.get("top_p", self.top_p),
            stop=stop or self.stop,
            stream=True,
            presence_penalty=kwargs.get("presence_penalty", self.presence_penalty),
            frequency_penalty=kwargs.get("frequency_penalty", self.frequency_penalty),
        )
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self._get_api_url(),
                    headers=self._get_headers(),
                    json=request.to_dict(),
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data)
                                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunk = ChatGenerationChunk(
                                        message=AIMessageChunk(content=content)
                                    )
                                    if run_manager:
                                        await run_manager.on_llm_new_token(content)
                                    yield chunk
                            except json.JSONDecodeError:
                                continue
                                
        except aiohttp.ClientError as e:
            logger.error(f"Async streaming request failed: {e}")
            raise RuntimeError(f"ChatAIServer async streaming request failed: {e}")
    
    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: dict | str | bool | None = None,
        strict: bool | None = None,
        parallel_tool_calls: bool | None = None,
        response_format: _DictOrPydanticClass | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        """Bind tool-like objects to this chat model.

        Assumes model is compatible with OpenAI tool-calling API.

        Args:
            tools: A list of tool definitions to bind to this chat model.

                Supports any tool definition handled by [`convert_to_openai_tool`][langchain_core.utils.function_calling.convert_to_openai_tool].
            tool_choice: Which tool to require the model to call. Options are:

                - `str` of the form `'<<tool_name>>'`: calls `<<tool_name>>` tool.
                - `'auto'`: automatically selects a tool (including no tool).
                - `'none'`: does not call a tool.
                - `'any'` or `'required'` or `True`: force at least one tool to be called.
                - `dict` of the form `{"type": "function", "function": {"name": <<tool_name>>}}`: calls `<<tool_name>>` tool.
                - `False` or `None`: no effect, default OpenAI behavior.
            strict: If `True`, model output is guaranteed to exactly match the JSON Schema
                provided in the tool definition. The input schema will also be validated according to the
                [supported schemas](https://platform.openai.com/docs/guides/structured-outputs/supported-schemas?api-mode=responses#supported-schemas).
                If `False`, input schema will not be validated and model output will not
                be validated. If `None`, `strict` argument will not be passed to the model.
            parallel_tool_calls: Set to `False` to disable parallel tool use.
                Defaults to `None` (no specification, which allows parallel tool use).
            response_format: Optional schema to format model response. If provided
                and the model does not call a tool, the model will generate a
                [structured response](https://platform.openai.com/docs/guides/structured-outputs).
            kwargs: Any additional parameters are passed directly to `bind`.
        """  # noqa: E501
        if parallel_tool_calls is not None:
            kwargs["parallel_tool_calls"] = parallel_tool_calls
        formatted_tools = [
            convert_to_openai_tool(tool, strict=strict) for tool in tools
        ]
        tool_names = []
        for tool in formatted_tools:
            if "function" in tool:
                tool_names.append(tool["function"]["name"])
            elif "name" in tool:
                tool_names.append(tool["name"])
            else:
                pass
        if tool_choice:
            if isinstance(tool_choice, str):
                # tool_choice is a tool/function name
                if tool_choice in tool_names:
                    tool_choice = {
                        "type": "function",
                        "function": {"name": tool_choice},
                    }
                # 'any' is not natively supported by OpenAI API.
                # We support 'any' since other models use this instead of 'required'.
                elif tool_choice == "any":
                    tool_choice = "required"
                else:
                    pass
            elif isinstance(tool_choice, bool):
                tool_choice = "required"
            elif isinstance(tool_choice, dict):
                pass
            else:
                msg = (
                    f"Unrecognized tool_choice type. Expected str, bool or dict. "
                    f"Received: {tool_choice}"
                )
                raise ValueError(msg)
            kwargs["tool_choice"] = tool_choice

        if response_format:
            if (
                isinstance(response_format, dict)
                and response_format.get("type") == "json_schema"
                and "schema" in response_format.get("json_schema", {})
            ):
                # compat with langchain.agents.create_agent response_format, which is
                # an approximation of OpenAI format
                strict = response_format["json_schema"].get("strict", None)
                response_format = cast(dict, response_format["json_schema"]["schema"])
            kwargs["response_format"] = _convert_to_openai_response_format(
                response_format, strict=strict
            )
        return super().bind(tools=formatted_tools, **kwargs)



# Convenience factory function
def create_chat_model(
    model: str = "gpt-4o",
    server_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> ChatAIServer:
    """
    Factory function to create a ChatAIServer instance.
    
    Args:
        model: Model identifier
        server_url: Jarvis server URL (default from environment)
        auth_token: Authentication token (default from environment)
        **kwargs: Additional model configuration
        
    Returns:
        Configured ChatAIServer instance
    """
    config = {"model": model}
    
    if server_url:
        config["server_url"] = server_url
    if auth_token:
        config["auth_token"] = auth_token
    if api_key:
        config["api_key"] = api_key
        
    config.update(kwargs)
    
    return ChatAIServer(**config)


async def main():
    model = create_chat_model(
        model='qwen3:latest',
        server_url='http://localhost:8080',
        auth_token="sk-8b9514c137d742b48624ed6bb1b97087",
    )
    response = await model._agenerate([
        SystemMessage(content='You are a helpful assistant.'),
        HumanMessage(content='who is shah rukh khan?')
    ])
    print(response.generations[0].message.content)
if __name__ == "__main__":
    import asyncio
    # Test the ChatAIServer
    asyncio.run(main())