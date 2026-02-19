"""Tool system for the General-Purpose Agentic AI"""

import asyncio
import logging
import inspect
import os
from typing import Dict, Any, List, Optional, Callable, Type, Union
from pydantic import BaseModel, Field, create_model
import datetime

logger = logging.getLogger(__name__)

class BaseTool(BaseModel):
    """Abstract base class for all tools"""
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None
    
    async def run(self, **kwargs) -> Any:
        """Run the tool with the given arguments"""
        raise NotImplementedError("Subclasses must implement run()")

class ToolRegistry:
    """Registry for managing and discovering tools"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance.tools = {}
        return cls._instance
    
    def register_tool(self, tool: BaseTool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools"""
        return list(self.tools.values())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get definitions for all tools (for LLM context)"""
        definitions = []
        for tool in self.tools.values():
            defn = {
                "name": tool.name,
                "description": tool.description,
            }
            if tool.args_schema:
                defn["parameters"] = tool.args_schema.schema()
            definitions.append(defn)
        return definitions

# --- Default Tool Implementations ---

class WebSearchSchema(BaseModel):
    query: str = Field(..., description="The search query to look up on the web")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for real-time information, news, and facts."
    args_schema: Type[BaseModel] = WebSearchSchema
    
    async def run(self, query: str) -> Any:
        from langchain_community.tools import DuckDuckGoSearchRun
        search = DuckDuckGoSearchRun()
        # Run in thread to avoid blocking loop
        return await asyncio.to_thread(search.run, query)

class CalculatorSchema(BaseModel):
    expression: str = Field(..., description="The mathematical expression to evaluate (e.g., '2 + 2 * 5')")

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Perform mathematical calculations and evaluate expressions."
    args_schema: Type[BaseModel] = CalculatorSchema
    
    async def run(self, expression: str) -> Any:
        try:
            # Simple and relatively safe eval for math
            # In a real production system, use a safer parser like 'simpleeval'
            result = eval(expression, {"__builtins__": None}, {})
            return {"result": result}
        except Exception as e:
            return {"error": f"Calculation failed: {str(e)}"}

class FileIOSchema(BaseModel):
    operation: str = Field(..., description="The operation to perform: 'read' or 'write'")
    filename: str = Field(..., description="The name/path of the file")
    content: Optional[str] = Field(None, description="The content to write (required for 'write' operation)")
    allow_write: bool = Field(False, description="Explicitly allow write operations")

class FileIOTool(BaseTool):
    name: str = "file_io"
    description: str = "Read from or write to local files (restricted to allowed directories)."
    args_schema: Type[BaseModel] = FileIOSchema
    
    async def run(self, operation: str, filename: str, content: Optional[str] = None, allow_write: bool = False) -> Any:
        # TODO: Implement strict directory check
        allowed_dir = os.path.abspath("data") # Or similar
        full_path = os.path.abspath(filename)
            
        try:
            if operation == "read":
                def _read():
                    with open(filename, 'r', encoding='utf-8') as f:
                        return f.read()
                data = await asyncio.to_thread(_read)
                return {"content": data}
            elif operation == "write":
                if not allow_write and not os.getenv("JARVIS_ALLOW_FILE_WRITE"):
                    return {"error": "Permission required for file write. Set JARVIS_ALLOW_FILE_WRITE=1 or pass allow_write=true."}
                if content is None:
                    return {"error": "Content required for write operation"}
                def _write():
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return True
                await asyncio.to_thread(_write)
                return {"success": True}
        except Exception as e:
            return {"error": f"File operation failed: {str(e)}"}

class KnowledgeLookupSchema(BaseModel):
    query: str = Field(..., description="The query to look up in the internal knowledge base")

class KnowledgeLookupTool(BaseTool):
    name: str = "knowledge_lookup"
    description: str = "Look up information in the internal Jarvis documentation and knowledge base."
    args_schema: Type[BaseModel] = KnowledgeLookupSchema
    
    async def run(self, query: str) -> Any:
        from mem0 import AsyncMemory


        mem_config = {
            "llm": {
                "provider": "litellm",
                "config": {
                    "model": "huggingface/microsoft/phi-4-mini-instruct",

                }
            },
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": "multi-qa-MiniLM-L6-cos-v1"
                }
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "jarvis",
                    "path": pathjoin(jarvis_cache,"memory"),
                }
            }
        }
        memory= AsyncMemory.from_config(mem_config)
        memories = memory.search(query, user_id=user_id)
        if memories and isinstance(memories, dict) and 'results' in memories:
            memory_context = "\n".join([f"- {m['text']}" for m in memories['results'] if isinstance(m, dict) and 'text' in m])
        elif isinstance(memories, list):
            memory_context = "\n".join([f"- {m['text']}" for m in memories if isinstance(m, dict) and 'text' in m])
        if  memory_context:
            return {"results": memory_context}
        return {"results": ["No matching information found in local knowledge base. Use web_search for external info."]}

class WeatherLookupSchema(BaseModel):
    location: str = Field(..., description="Location name, e.g., 'New York, NY' or 'London'")

class WeatherLookupTool(BaseTool):
    name: str = "weather_lookup"
    description: str = "Fetch real-time weather for a location using public APIs."
    args_schema: Type[BaseModel] = WeatherLookupSchema

    async def run(self, location: str) -> Any:
        import requests
        try:
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_resp = await asyncio.to_thread(requests.get, geo_url, params={"name": location, "count": 1})
            geo_data = geo_resp.json() if geo_resp.ok else {}
            results = geo_data.get("results") or []
            if not results:
                return {"error": f"Location not found: {location}"}
            loc = results[0]
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            weather_url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            }
            weather_resp = await asyncio.to_thread(requests.get, weather_url, params=params)
            weather = weather_resp.json() if weather_resp.ok else {}
            return {"location": loc, "weather": weather.get("current", {}), "timestamp": weather.get("current", {}).get("time")}
        except Exception as e:
            return {"error": f"Weather lookup failed: {str(e)}"}

class NewsSearchSchema(BaseModel):
    query: str = Field(..., description="Search query for news")
    limit: int = Field(10, description="Max number of articles to return")

class NewsSearchTool(BaseTool):
    name: str = "news_search"
    description: str = "Fetch latest news articles via public RSS feeds."
    args_schema: Type[BaseModel] = NewsSearchSchema

    async def run(self, query: str, limit: int = 10) -> Any:
        try:
            import feedparser
            import urllib.parse
            q = urllib.parse.quote_plus(query)
            url = f"https://news.google.com/rss/search?q={q}"
            feed = await asyncio.to_thread(feedparser.parse, url)
            entries = []
            for entry in feed.entries[: max(1, min(limit, 50))]:
                entries.append({
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "published": entry.get("published"),
                    "source": entry.get("source", {}).get("title") if isinstance(entry.get("source"), dict) else None,
                })
            return {"query": query, "articles": entries}
        except Exception as e:
            return {"error": f"News search failed: {str(e)}"}


# Global registry instance
registry = ToolRegistry()

# Auto-register default tools
import os
registry.register_tool(WebSearchTool())
registry.register_tool(CalculatorTool())
registry.register_tool(FileIOTool())
registry.register_tool(KnowledgeLookupTool())
registry.register_tool(WeatherLookupTool())
registry.register_tool(NewsSearchTool())

# Optional tool extensions (vision/context)
try:
    from .vision_tools import VisionAnalyzeTool, VisionPerceptionTool
    from .context_tools import SystemContextTool, SessionContextTool

    registry.register_tool(VisionAnalyzeTool())
    registry.register_tool(VisionPerceptionTool())
    registry.register_tool(SystemContextTool())
    registry.register_tool(SessionContextTool())
except Exception as exc:
    logger.warning("Optional tools not registered: %s", exc)
