import asyncio
from typing import List, Tuple

from ..agent.base import RAGAgent, describe_class
from ..agent.collection_router import CollectionRouter
from ..embedding.base import BaseEmbedding
from ..llm.base import BaseLLM
from ..utils import log
from ..vector_db import RetrievalResult
from ..vector_db.base import BaseVectorDB, deduplicate_results

SUB_QUERY_PROMPT = """To answer this question more comprehensively, please break down the original question into up to four sub-questions. Return as list of str.
If this is a very simple question and no decomposition is necessary, then keep the only one original question in the python code list.

Original Question: {original_query}


<EXAMPLE>
Example input:
"Explain deep learning"

Example output:
[
    "What is deep learning?",
    "What is the difference between deep learning and machine learning?",
    "What is the history of deep learning?"
]
</EXAMPLE>

Provide your response in a python code list of str format:
"""

RERANK_PROMPT = """Based on the query questions and the retrieved chunk, to determine whether the chunk is helpful in answering any of the query question, you can only return "YES" or "NO", without any other information.

Query Questions: {query}
Retrieved Chunk: {retrieved_chunk}

Is the chunk helpful in answering the any of the questions?
"""


REFLECT_PROMPT = """Determine whether additional search queries are needed based on the original query, previous sub queries, and all retrieved document chunks. If further research is required, provide a Python list of up to 3 search queries. If no further research is required, return an empty list.

If the original query is to write a report, then you prefer to generate some further queries, instead return an empty list.

Original Query: {question}

Previous Sub Queries: {mini_questions}

Related Chunks: 
{mini_chunk_str}

Respond exclusively in valid List of str format without any other text."""


SUMMARY_PROMPT = """You are a AI content analysis expert, good at summarizing content. Please summarize a specific and detailed answer or report based on the previous queries and the retrieved document chunks.

Original Query: {question}

Previous Sub Queries: {mini_questions}

Related Chunks: 
{mini_chunk_str}

"""


@describe_class(
    "This agent is suitable for handling general and simple queries, such as given a topic and then writing a report, survey, or article."
)
class DeepSearch(RAGAgent):
    """
    Deep Search agent implementation for comprehensive information retrieval.

    This agent performs a thorough search through the knowledge base, analyzing
    multiple aspects of the query to provide comprehensive and detailed answers.
    """

    def __init__(
        self,
        llm: BaseLLM,
        embedding_model: BaseEmbedding,
        vector_db: BaseVectorDB,
        max_iter: int = 3,
        route_collection: bool = True,
        text_window_splitter: bool = True,
        **kwargs,
    ):
        """
        Initialize the DeepSearch agent.

        Args:
            llm: The language model to use for generating answers.
            embedding_model: The embedding model to use for query embedding.
            vector_db: The vector database to search for relevant documents.
            max_iter: The maximum number of iterations for the search process.
            route_collection: Whether to use a collection router for search.
            text_window_splitter: Whether to use text_window splitter.
            **kwargs: Additional keyword arguments for customization.
        """
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.max_iter = max_iter
        self.route_collection = route_collection
        self.collection_router = CollectionRouter(
            llm=self.llm, vector_db=self.vector_db, dim=embedding_model.dimension
        )
        self.text_window_splitter = text_window_splitter
        self.web_search = kwargs.get("web_search")
        self.web_crawler = kwargs.get("web_crawler")

    def _generate_sub_queries(self, original_query: str) -> Tuple[List[str], int]:
        chat_response = self.llm.chat(
            messages=[
                {"role": "user", "content": SUB_QUERY_PROMPT.format(original_query=original_query)}
            ]
        )
        response_content = self.llm.remove_think(chat_response.content)
        return self.llm.literal_eval(response_content), chat_response.total_tokens

    async def _search_chunks_from_vectordb(self, query: str, sub_queries: List[str]):
        consume_tokens = 0
        if self.route_collection:
            selected_collections, n_token_route = self.collection_router.invoke(
                query=query, dim=self.embedding_model.dimension
            )
        else:
            selected_collections = self.collection_router.all_collections
            n_token_route = 0
        consume_tokens += n_token_route

        all_retrieved_results = []
        query_vector = self.embedding_model.embed_query(query)
        for collection in selected_collections:
            log.color_print(f"<search> Search [{query}] in [{collection}]...  </search>\n")
            retrieved_results = self.vector_db.search_data(
                collection=collection, vector=query_vector, query_text=query
            )
            if not retrieved_results or len(retrieved_results) == 0:
                log.color_print(
                    f"<search> No relevant document chunks found in '{collection}'! </search>\n"
                )
                continue
            accepted_chunk_num = 0
            references = set()
            for retrieved_result in retrieved_results:
                chat_response = self.llm.chat(
                    messages=[
                        {
                            "role": "user",
                            "content": RERANK_PROMPT.format(
                                query=[query] + sub_queries,
                                retrieved_chunk=f"<chunk>{retrieved_result.text}</chunk>",
                            ),
                        }
                    ]
                )
                consume_tokens += chat_response.total_tokens
                response_content = self.llm.remove_think(chat_response.content).strip()
                if "YES" in response_content and "NO" not in response_content:
                    all_retrieved_results.append(retrieved_result)
                    accepted_chunk_num += 1
                    references.add(retrieved_result.reference)
            if accepted_chunk_num > 0:
                log.color_print(
                    f"<search> Accept {accepted_chunk_num} document chunk(s) from references: {list(references)} </search>\n"
                )
            else:
                log.color_print(
                    f"<search> No document chunk accepted from '{collection}'! </search>\n"
                )
        return all_retrieved_results, consume_tokens

    def _generate_gap_queries(
        self, original_query: str, all_sub_queries: List[str], all_chunks: List[RetrievalResult]
    ) -> Tuple[List[str], int]:
        reflect_prompt = REFLECT_PROMPT.format(
            question=original_query,
            mini_questions=all_sub_queries,
            mini_chunk_str=self._format_chunk_texts([chunk.text for chunk in all_chunks])
            if len(all_chunks) > 0
            else "NO RELATED CHUNKS FOUND.",
        )
        chat_response = self.llm.chat([{"role": "user", "content": reflect_prompt}])
        response_content = self.llm.remove_think(chat_response.content)
        return self.llm.literal_eval(response_content), chat_response.total_tokens

    def retrieve(self, original_query: str, **kwargs) -> Tuple[List[RetrievalResult], int, dict]:
        """
        Retrieve relevant documents from the knowledge base for the given query.

        This method performs a deep search through the vector database to find
        the most relevant documents for answering the query.

        Args:
            original_query (str): The query to search for.
            **kwargs: Additional keyword arguments for customizing the retrieval.

        Returns:
            Tuple[List[RetrievalResult], int, dict]: A tuple containing:
                - A list of retrieved document results
                - The token usage for the retrieval operation
                - Additional information about the retrieval process
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return asyncio.run_coroutine_threadsafe(
                self.async_retrieve(original_query, **kwargs), loop
            ).result()
        else:
            return asyncio.run(self.async_retrieve(original_query, **kwargs))

    async def async_retrieve(
        self, original_query: str, **kwargs
    ) -> Tuple[List[RetrievalResult], int, dict]:
        max_iter = kwargs.pop("max_iter", self.max_iter)
        ### SUB QUERIES ###
        log.color_print(f"<query> {original_query} </query>\n")
        all_search_res = []
        all_sub_queries = []
        total_tokens = 0

        sub_queries, used_token = self._generate_sub_queries(original_query)
        total_tokens += used_token
        if not sub_queries:
            print("No sub queries were generated by the LLM. Using original query as fallback.")
            sub_queries = [original_query]
        
        print(f"<think> Break down the original query into new sub queries: {sub_queries}</think>\n")
        all_sub_queries.extend(sub_queries)
        sub_gap_queries = sub_queries

        for iter in range(max_iter):
            print(f">> Iteration: {iter + 1}\n")
            search_res_from_vectordb = []
            search_res_from_internet = []

            # Create all search tasks for vectordb
            vectordb_tasks = [
                self._search_chunks_from_vectordb(query, sub_gap_queries)
                for query in sub_gap_queries
            ]
            
            # Create internet search tasks if available
            internet_tasks = []
            if self.web_search and self.web_crawler:
                print("DEBUG: web_search and web_crawler are set, creating internet tasks")
                internet_tasks = [
                    self._search_chunks_from_internet(query, sub_gap_queries)
                    for query in sub_gap_queries
                ]
            else:
                print(f"DEBUG: web_search={self.web_search}, web_crawler={self.web_crawler}")
            
            # Execute all tasks in parallel
            all_results = await asyncio.gather(*(vectordb_tasks + internet_tasks))
            
            # Split results
            vectordb_results = all_results[:len(vectordb_tasks)]
            internet_results = all_results[len(vectordb_tasks):]

            # Merge vectordb results
            for result in vectordb_results:
                search_res, consumed_token = result
                total_tokens += consumed_token
                search_res_from_vectordb.extend(search_res)

            # Merge internet results
            for result in internet_results:
                search_res, consumed_token = result
                total_tokens += consumed_token
                search_res_from_internet.extend(search_res)

            search_res_from_vectordb = deduplicate_results(search_res_from_vectordb)
            search_res_from_internet = deduplicate_results(search_res_from_internet)
            all_search_res.extend(search_res_from_vectordb + search_res_from_internet)
            if iter == max_iter - 1:
                log.color_print("<think> Exceeded maximum iterations. Exiting. </think>\n")
                break
            ### REFLECTION & GET GAP QUERIES ###
            log.color_print("<think> Reflecting on the search results... </think>\n")
            sub_gap_queries, consumed_token = self._generate_gap_queries(
                original_query, all_sub_queries, all_search_res
            )
            total_tokens += consumed_token
            if not sub_gap_queries or len(sub_gap_queries) == 0:
                log.color_print("<think> No new search queries were generated. Exiting. </think>\n")
                break
            else:
                log.color_print(
                    f"<think> New search queries for next iteration: {sub_gap_queries} </think>\n"
                )
                all_sub_queries.extend(sub_gap_queries)

        all_search_res = deduplicate_results(all_search_res)
        additional_info = {"all_sub_queries": all_sub_queries}
        return all_search_res, total_tokens, additional_info

    def query(self, query: str, **kwargs) -> Tuple[str, List[RetrievalResult], int]:
        """
        Query the agent and generate an answer based on retrieved documents.

        This method retrieves relevant documents and uses the language model
        to generate a comprehensive answer to the query.

        Args:
            query (str): The query to answer.
            **kwargs: Additional keyword arguments for customizing the query process.

        Returns:
            Tuple[str, List[RetrievalResult], int]: A tuple containing:
                - The generated answer
                - A list of retrieved document results
                - The total token usage
        """
        all_retrieved_results, n_token_retrieval, additional_info = self.retrieve(query, **kwargs)
        if not all_retrieved_results or len(all_retrieved_results) == 0:
            return f"No relevant information found for query '{query}'.", [], n_token_retrieval
        all_sub_queries = additional_info["all_sub_queries"]
        chunk_texts = []
        for chunk in all_retrieved_results:
            if self.text_window_splitter and "wider_text" in chunk.metadata:
                chunk_texts.append(chunk.metadata["wider_text"])
            else:
                chunk_texts.append(chunk.text)
        log.color_print(
            f"<think> Summarize answer from all {len(all_retrieved_results)} retrieved chunks... </think>\n"
        )
        summary_prompt = SUMMARY_PROMPT.format(
            question=query,
            mini_questions=all_sub_queries,
            mini_chunk_str=self._format_chunk_texts(chunk_texts),
        )
        chat_response = self.llm.chat([{"role": "user", "content": summary_prompt}])
        log.color_print("\n==== FINAL ANSWER====\n")
        log.color_print(self.llm.remove_think(chat_response.content))
        return (
            self.llm.remove_think(chat_response.content),
            all_retrieved_results,
            n_token_retrieval + chat_response.total_tokens,
        )

    async def async_query(self, query: str, **kwargs) -> Tuple[str, List[RetrievalResult], int]:
        """
        Async query the agent and generate an answer based on retrieved documents.

        Args:
            query (str): The query to answer.
            **kwargs: Additional keyword arguments for customizing the query process.

        Returns:
            Tuple[str, List[RetrievalResult], int]: A tuple containing:
                - The generated answer
                - A list of retrieved document results
                - The total token usage
        """
        all_retrieved_results, n_token_retrieval, additional_info = await self.async_retrieve(
            query, **kwargs
        )
        if not all_retrieved_results or len(all_retrieved_results) == 0:
            return f"No relevant information found for query '{query}'.", [], n_token_retrieval
        all_sub_queries = additional_info["all_sub_queries"]
        chunk_texts = []
        for chunk in all_retrieved_results:
            if self.text_window_splitter and "wider_text" in chunk.metadata:
                chunk_texts.append(chunk.metadata["wider_text"])
            else:
                chunk_texts.append(chunk.text)
        log.color_print(
            f"<think> Summarize answer from all {len(all_retrieved_results)} retrieved chunks... </think>\n"
        )
        summary_prompt = SUMMARY_PROMPT.format(
            question=query,
            mini_questions=all_sub_queries,
            mini_chunk_str=self._format_chunk_texts(chunk_texts),
        )
        chat_response = self.llm.chat([{"role": "user", "content": summary_prompt}])
        log.color_print("\n==== FINAL ANSWER====\n")
        log.color_print(self.llm.remove_think(chat_response.content))
        return (
            self.llm.remove_think(chat_response.content),
            all_retrieved_results,
            n_token_retrieval + chat_response.total_tokens,
        )

    def _format_chunk_texts(self, chunk_texts: List[str]) -> str:
        chunk_str = ""
        for i, chunk in enumerate(chunk_texts):
            chunk_str += f"""<chunk_{i}>\n{chunk}\n</chunk_{i}>\n"""
        return chunk_str

    async def _search_chunks_from_internet(self, query: str, sub_queries: List[str]):
        if not self.web_search or not self.web_crawler:
            return [], 0
            
        consume_tokens = 0
        log.color_print(f"<search> Internet Search [{query}]... </search>\n")
        
        search_results = await self.web_search.async_search(query)
        if not search_results:
            return [], 0
            
        urls = [r["url"] for r in search_results[:3]] # Limit to top 3 URLs for efficiency
        log.color_print(f"<search> Crawling {len(urls)} URLs from internet... </search>\n")
        
        # Use the crawler to get content
        documents = await self.web_crawler._async_crawl_many(urls)
        
        # Split documents into chunks
        from ..loader.splitter import split_docs_to_chunks
        chunks = split_docs_to_chunks(documents)
        
        # Convert chunks to RetrievalResults
        internet_retrieved_results = []
        for chunk in chunks:
            # Re-rank or filter chunks
            chat_response = self.llm.chat(
                messages=[
                    {
                        "role": "user",
                        "content": RERANK_PROMPT.format(
                            query=[query] + sub_queries,
                            retrieved_chunk=f"<chunk>{chunk.text}</chunk>",
                        ),
                    }
                ]
            )
            consume_tokens += chat_response.total_tokens
            response_content = self.llm.remove_think(chat_response.content).strip()
            if "YES" in response_content and "NO" not in response_content:
                # We need a dummy vector or use embedding model if we want to store them, 
                # but for online search we can just pass them as results.
                from ..vector_db import RetrievalResult
                import numpy as np
                res = RetrievalResult(
                    embedding=np.zeros(self.embedding_model.dimension),
                    text=chunk.text,
                    reference=chunk.reference,
                    metadata=chunk.metadata,
                    score=1.0 # High score for internet results
                )
                internet_retrieved_results.append(res)
                
        return internet_retrieved_results, consume_tokens
