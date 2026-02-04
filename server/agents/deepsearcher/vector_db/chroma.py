import os
import uuid
from typing import List, Optional, Union

import numpy as np

from ..loader.splitter import Chunk
from ..utils import log
from ..vector_db.base import BaseVectorDB, CollectionInfo, RetrievalResult

DEFAULT_COLLECTION_NAME = "deepsearcher"

class Chroma(BaseVectorDB):
    """Vector DB implementation powered by [ChromaDB](https://www.trychroma.com/)"""

    def __init__(
        self,
        path: str = "./chroma_db",
        default_collection: str = DEFAULT_COLLECTION_NAME,
        **kwargs,
    ):
        """
        Initialize the Chroma client.

        Args:
            path (str, optional): Path to the persistence directory. Defaults to "./chroma_db".
            default_collection (str, optional): Default collection name. Defaults to "deepsearcher".
            **kwargs: Additional keyword arguments to pass to the Chroma client.
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as original_error:
            raise ImportError(
                "ChromaDB is not installed. Install it using: pip install chromadb"
            ) from original_error

        super().__init__(default_collection)
        self.client = chromadb.PersistentClient(path=path, settings=Settings(allow_reset=True))
        self.default_collection = default_collection

    def init_collection(
        self,
        dim: int,
        collection: Optional[str] = None,
        description: Optional[str] = "",
        force_new_collection: bool = False,
        *args,
        **kwargs,
    ):
        """
        Initialize a collection in ChromaDB.

        Args:
            dim (int): Dimension of the vector embeddings (not used directly by Chroma but kept for interface consistency).
            collection (Optional[str], optional): Collection name.
            description (Optional[str], optional): Collection description. Defaults to "".
            force_new_collection (bool, optional): Whether to force create a new collection if it already exists. Defaults to False.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        collection_name = collection or self.default_collection
        
        try:
            if force_new_collection:
                try:
                    self.client.delete_collection(name=collection_name)
                    log.color_print(f"Deleted existing collection [{collection_name}]")
                except ValueError:
                    pass # Collection doesn't exist
            
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": description} if description else None
            )
            log.color_print(f"Initialised Chroma collection [{collection_name}] successfully")
        except Exception as e:
            log.critical(f"Failed to init Chroma collection, error info: {e}")

    def insert_data(
        self,
        collection: Optional[str],
        chunks: List[Chunk],
        batch_size: int = 256,
        *args,
        **kwargs,
    ):
        """
        Insert data into a Chroma collection.

        Args:
            collection (Optional[str]): Collection name.
            chunks (List[Chunk]): List of Chunk objects to insert.
            batch_size (int, optional): Number of chunks to insert in each batch. Defaults to 256.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        collection_name = collection or self.default_collection
        coll = self.client.get_collection(name=collection_name)

        try:
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i : i + batch_size]
                
                coll.add(
                    ids=[uuid.uuid4().hex for _ in batch_chunks],
                    embeddings=[chunk.embedding for chunk in batch_chunks],
                    documents=[chunk.text for chunk in batch_chunks],
                    metadatas=[
                        {
                            "reference": chunk.reference,
                            **chunk.metadata
                        } for chunk in batch_chunks
                    ]
                )
        except Exception as e:
            log.critical(f"Failed to insert data into Chroma, error info: {e}")

    def search_data(
        self,
        collection: Optional[str],
        vector: Union[np.array, List[float]],
        top_k: int = 5,
        *args,
        **kwargs,
    ) -> List[RetrievalResult]:
        """
        Search for similar vectors in a Chroma collection.

        Args:
            collection (Optional[str]): Collection name.
            vector (Union[np.array, List[float]]): Query vector for similarity search.
            top_k (int, optional): Number of results to return. Defaults to 5.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List[RetrievalResult]: List of retrieval results containing similar vectors.
        """
        collection_name = collection or self.default_collection
        coll = self.client.get_collection(name=collection_name)

        try:
            results = coll.query(
                query_embeddings=[vector if isinstance(vector, list) else vector.tolist()],
                n_results=top_k,
                include=["embeddings", "documents", "metadatas", "distances"]
            )

            retrieval_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for idx in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][idx]
                    reference = metadata.pop("reference", "")
                    
                    retrieval_results.append(
                        RetrievalResult(
                            embedding=np.array(results["embeddings"][0][idx]),
                            text=results["documents"][0][idx],
                            reference=reference,
                            score=results["distances"][0][idx],
                            metadata=metadata,
                        )
                    )
            return retrieval_results
        except Exception as e:
            log.critical(f"Failed to search Chroma data, error info: {e}")
            return []

    def list_collections(self, *args, **kwargs) -> List[CollectionInfo]:
        """
        List all collections in the Chroma database.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            List[CollectionInfo]: List of collection information objects.
        """
        try:
            collections = self.client.list_collections()
            return [
                CollectionInfo(
                    collection_name=c.name,
                    description=c.metadata.get("description", "") if c.metadata else ""
                )
                for c in collections
            ]
        except Exception as e:
            log.critical(f"Failed to list Chroma collections, error info: {e}")
            return []

    def clear_db(self, collection: Optional[str] = None, *args, **kwargs):
        """
        Clear (drop) a collection from the Chroma database.

        Args:
            collection (str, optional): Collection name to drop.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        collection_name = collection or self.default_collection
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            log.warning(f"Failed to drop Chroma collection, error info: {e}")
