"""Deep Research Agent powered by LangChain for autonomous, citation-backed information retrieval."""

import os
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_community.tools import DuckDuckGoSearchRun, ArxivQueryRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
try:
    from mem0 import Memory
except Exception:  # pragma: no cover - optional dependency
    Memory = None

from .base_agent import BaseAgent, Task, AgentResponse, AgentStatus

# Logging setup
logger = logging.getLogger(__name__)

class ResearchPlan(BaseModel):
    is_deep: bool = Field(description="Whether the query requires deep multi-source research")
    sub_questions: List[str] = Field(description="A list of specific sub-questions to research independently")
    reasoning: str = Field(description="Reasoning behind why shallow or deep research was chosen")

class Fact(BaseModel):
    statement: str = Field(description="A factual statement found in the research")
    source_index: int = Field(description="The index of the source this fact was found in")
    uncertainty: Optional[str] = Field(None, description="Note any uncertainty or contradictions found for this fact")

class DeepSearchAgent(BaseAgent):
    """
    Agent specialized in deep multi-source research and synthesis.
    Implements a Perplexity-style workflow:
    1. Query Decomposition
    2. Parallel Multi-source Retrieval (Web + Arxiv)
    3. Reasoning and Cross-verification
    4. Citation-backed Synthesis
    """

    def __init__(self):
        super().__init__(
            agent_id="deep_research_agent_v1",
            name="Deep Research Agent",
            description="Autonomous AI agent that conducts in-depth, multi-step investigations on user-defined topics. It browses hundreds of sources, analyzes text, images, and PDFs, and synthesizes findings into comprehensive, citation-rich reports."
        )
        self.web_search = DuckDuckGoSearchRun()
        self.arxiv_search = ArxivQueryRun()
        from pathlib import Path
        from os.path import join as pathjoin,exists as pathexists
        cache_dir = Path().home()
        jarvis_cache = pathjoin(cache_dir,".jarvis")
        # Initialize mem0 Memory (optional)
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
        
        if Memory is None:
            logger.warning("DeepSearchAgent: mem0 not installed; memory features disabled.")
            self.memory = None
        else:
            try:
                self.memory = Memory.from_config(mem_config)
                logger.info("DeepSearchAgent: mem0 Memory initialized successfully with phi-4-mini.")
            except Exception as e:
                logger.warning(f"DeepSearchAgent: Failed to initialize mem0 Memory: {e}")
                self.memory = None

    def can_handle_task(self, task: Task) -> bool:
        """Determines if the task relates to research or general knowledge retrieval."""
        task_type = task.metadata.get("task_type", "")
        query = task.metadata.get("query", "").lower()
        keywords = ["research", "analyze", "explain", "who is", "what is", "current", "latest"]
        
        return task_type in ["web_search", "research", "information_retrieval"] or any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        """Orchestrates the research process."""
        self.status = AgentStatus.RUNNING
        query = task.metadata.get("query")
        task_id = task.metadata.get("parent_task_id") or task.id
        
        if not query:
            await self.emit_event("error_event", task_id, {
                "source": "deep_search",
                "agent": self.name,
                "message": "No query provided."
            })
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error="No query provided."
            )

        # 1. Search existing memories for context
        memory_context = ""
        user_id = task.metadata.get("user_id", "default_user")
        if self.memory:
            try:
                # Use user_id as suggested by mem0 docs for filtering
                memories = self.memory.search(query, user_id=user_id)
                if memories and isinstance(memories, dict) and 'results' in memories:
                    memory_context = "\n".join([f"- {m['text']}" for m in memories['results'] if isinstance(m, dict) and 'text' in m])
                    logger.info(f"Found {len(memories['results'])} relevant memories.")
                elif isinstance(memories, list):
                    memory_context = "\n".join([f"- {m['text']}" for m in memories if isinstance(m, dict) and 'text' in m])
                    logger.info(f"Found {len(memories)} relevant memories.")
            except Exception as e:
                logger.warning(f"DeepSearchAgent: Failed to search memories: {e}")
            

        llm = self.get_llm(task)
        await self.emit_event("active_agent", task_id, {"agent": self.name})
        await self.emit_event("agent_state", task_id, {"state": "executing", "agent": self.name})
        await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Starting deep research"})
        
        try:
            # 2. Analyze and Decompose Query (Now with memory context)
            research_plan = await self._create_research_plan(llm, query, memory_context)
            logger.info(f"Research Plan: {research_plan}")

            # 3. Execute Research (Multi-step reasoning approach)
            unique_sources = []
            max_steps = 2
            current_step = 0
            questions_to_search = research_plan.sub_questions + [query]
            
            while current_step < max_steps:
                current_step += 1
                logger.info(f"Research Step {current_step}/{max_steps}")
                
                await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": f"Searching sources (step {current_step})"})
                search_tasks = [self._research_question(q) for q in questions_to_search]
                results = await asyncio.gather(*search_tasks)
                
                new_sources = []
                for res in results:
                    new_sources.extend(res)
                
                unique_sources = self._deduplicate_sources(unique_sources + new_sources)
                
                # Check if we have enough info or if we should refine (Self-correction)
                if len(unique_sources) >= 5 or not research_plan.is_deep or current_step >= max_steps:
                    break
                
                # Refine: Generate follow-up questions if needed
                # (Simplification: just retry once for now if sources are low)
                logger.info("Insufficient sources found, attempting refinement step.")

            # 4. Reasoning and Synthesis
            await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Synthesizing findings"})
            final_report = await self._synthesize_findings(llm, query, unique_sources, memory_context)

            # 5. Store findings in memory
            if self.memory:
                try:
                    self.memory.add(f"Research on '{query}': {final_report}", user_id=user_id)
                    logger.info("Findings stored in memory.")
                except Exception as e:
                    logger.warning(f"Failed to store findings in memory: {e}")

            return AgentResponse(
                agent_id=self.agent_id,
                success=True,
                result=final_report
            )

        except Exception as e:
            logger.exception("Error in DeepSearchAgent")
            await self.emit_event("error_event", task_id, {
                "source": "deep_search",
                "agent": self.name,
                "message": str(e)
            })
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error=str(e)
            )
        finally:
            self.status = AgentStatus.COMPLETED

    async def _create_research_plan(self, llm: Any, query: str, memory_context: str = "") -> ResearchPlan:
        """Determines if deep research is needed and decomposes the query."""
        parser = JsonOutputParser(pydantic_object=ResearchPlan)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a research architect. Analyze the user query and decide if it needs 'shallow' or 'deep' research.\n"
                       "Shallow: Simple factual questions about well-known topics.\n"
                       "Deep: Complex, broad, analytical, or recent topics requiring multiple perspectives.\n"
                       "If deep, decompose the query into up to 5 specific, independent sub-questions.\n"
                       "CONTEXT FROM MEMORY (User preferences or previous facts):\n{memory_context}\n"
                       "{format_instructions}"),
            ("human", "{query}")
        ])
        
        chain = prompt | llm | parser
        result = await chain.ainvoke({
            "query": query,
            "memory_context": memory_context or "No previous context.",
            "format_instructions": parser.get_format_instructions()
        })
        
        # Ensure result is a ResearchPlan object
        if isinstance(result, dict):
            return ResearchPlan(**result)
        return result

    async def _research_question(self, question: str) -> List[Dict[str, str]]:
        """Performs search across multiple providers for a single question."""
        sources = []
        
        # Web Search
        try:
            web_results = await asyncio.to_thread(self.web_search.run, question)
            if web_results:
                sources.append({"content": web_results, "provider": "DuckDuckGo", "query": question})
        except Exception as e:
            logger.warning(f"Web search failed for '{question}': {e}")

        # Arxiv Search (Conditional: only for technical/academic sounding queries)
        academic_keywords = ["physics", "quantum", "algorithm", "paper", "study", "research", "neural", "ai", "math"]
        if any(k in question.lower() for k in academic_keywords):
            try:
                arxiv_results = await asyncio.to_thread(self.arxiv_search.run, question)
                if arxiv_results:
                    sources.append({"content": arxiv_results, "provider": "Arxiv", "query": question})
            except Exception as e:
                logger.warning(f"Arxiv search failed for '{question}': {e}")
                
        return sources

    def _deduplicate_sources(self, sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Deduplicates sources based on content similarity (simple approach for now)."""
        seen_content = set()
        unique = []
        for s in sources:
            # Hash first 200 chars to avoid exact duplicate snippets
            content_hash = hash(s["content"][:200])
            if content_hash not in seen_content:
                unique.append(s)
                seen_content.add(content_hash)
        return unique[:15] # Limit to top 15 sources

    async def _synthesize_findings(self, llm: Any, query: str, sources: List[Dict[str, str]], memory_context: str = "") -> str:
        """Synthesizes findings into a structured, cited report."""
        sources_text = "\n\n".join([f"SOURCE [{i+1}]: Provider: {s['provider']}\nContent: {s['content']}" for i, s in enumerate(sources)])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Research Assistant. Your goal is to provide a comprehensive, citation-backed answer.\n\n"
                       "GUIDELINES:\n"
                       "1. Accuracy first: Only claim what is supported by sources. Flag uncertainty if needed.\n"
                       "2. Citations: Use inline citations like [1], [2] corresponding to the source indexes provided.\n"
                       "3. Tone: Professional, analytical, objective.\n"
                       "4. Structure:\n"
                       "   - Restatement of Question\n"
                       "   - Researched Findings (organized by theme/topic)\n"
                       "   - Synthesis and Insights\n"
                       "   - Sources Section\n"
                       "   - Suggested Follow-up Questions\n\n"
                       "CONTEXT FROM MEMORY:\n{memory_context}\n\n"
                       "SOURCES:\n{sources}"),
            ("human", "Research Query: {query}")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "query": query,
            "memory_context": memory_context or "No previous context.",
            "sources": sources_text
        })
        
        return response.content
