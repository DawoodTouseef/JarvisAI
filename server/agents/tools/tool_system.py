"""Tool system for the General-Purpose Agentic AI"""

import asyncio
import logging
import inspect
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

class FileIOTool(BaseTool):
    name: str = "file_io"
    description: str = "Read from or write to local files (restricted to allowed directories)."
    args_schema: Type[BaseModel] = FileIOSchema
    
    async def run(self, operation: str, filename: str, content: Optional[str] = None) -> Any:
        # TODO: Implement strict directory check
        allowed_dir = os.path.abspath("data") # Or similar
        full_path = os.path.abspath(filename)
        
        # Simple security check (could be improved)
        # if not full_path.startswith(allowed_dir):
        #     return {"error": "Access denied: Filename outside allowed directory"}
            
        try:
            if operation == "read":
                def _read():
                    with open(filename, 'r', encoding='utf-8') as f:
                        return f.read()
                data = await asyncio.to_thread(_read)
                return {"content": data}
            elif operation == "write":
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
        # Mocking a knowledge lookup for now
        # In a real system, this would query a vector database (RAG)
        mock_kb = {
            "jarvis": "Jarvis is an advanced AI assistant designed for productivity and system control.",
            "creator": "Jarvis was designed by the AI systems architecture team.",
            "version": "Current version is 2.0 Agentic Alpha.",

        }
        query_lower = query.lower()
        results = [v for k, v in mock_kb.items() if k in query_lower]
        if results:
            return {"results": results}
        return {"results": ["No matching information found in local knowledge base. Use web_search for external info."]}



# Global registry instance
registry = ToolRegistry()

# Auto-register default tools
import os
registry.register_tool(WebSearchTool())
registry.register_tool(CalculatorTool())
registry.register_tool(FileIOTool())
registry.register_tool(KnowledgeLookupTool())

# Optional tool extensions (vision/context)
try:
    from .vision_tools import VisionAnalyzeTool
    from .context_tools import SystemContextTool, SessionContextTool

    registry.register_tool(VisionAnalyzeTool())
    registry.register_tool(SystemContextTool())
    registry.register_tool(SessionContextTool())
except Exception as exc:
    logger.warning("Optional tools not registered: %s", exc)
