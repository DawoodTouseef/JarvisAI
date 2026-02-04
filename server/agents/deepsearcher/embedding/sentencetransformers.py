import os
from typing import List

from openai._types import NOT_GIVEN

from ..embedding.base import BaseEmbedding


SENETENCETRANSFORMERS_MODEL_DIM_MAP = {
    "sentence-transformers/all-MiniLM-L6-v2": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


class SentenceTransformersEmbedding(BaseEmbedding):
    """
    SentenceTransformers embedding model implementation.

    This class provides an interface to the SentenceTransformers embedding API, which offers
    various embedding models for text processing.

    For more information, see:
    https://platform.SentenceTransformers.com/docs/guides/embeddings/use-cases
    """

    def __init__(self, model: str = "all-MiniLM-L6-v2", **kwargs):
        """
        Initialize the SentenceTransformers embedding model.

        Args:
            model (str): The model identifier to use for embeddings. Default is "all-MiniLM-L6-v2".
            **kwargs: Additional keyword arguments.
                - api_key (str, optional): The SentenceTransformers API key. If not provided,
                  it will be read from the SentenceTransformers_API_KEY environment variable.
                - base_url (str, optional): The base URL for the SentenceTransformers API. If not provided,
                  it will be read from the SentenceTransformers_BASE_URL environment variable.
                - model_name (str, optional): Alternative way to specify the model.
                - dimension (int, optional): The dimension of the embedding vectors.
                  If not provided, the default dimension for the model will be used.
                - azure_endpoint (str, optional): If provided, use Azure SentenceTransformers instead.
                - api_version (str, optional): Azure API version to use. Default is "2023-05-15".

        Notes:
            Available models:
                - 'all-MiniLM-L6-v2': No dimension needed, default is 1536
                - 'text-embedding-3-small': dimensions from 512 to 1536, default is 1536
                - 'text-embedding-3-large': dimensions from 1024 to 3072, default is 3072
        """

        if "model_name" in kwargs and (not model or model == "all-MiniLM-L6-v2"):
            model = kwargs.pop("model_name")

        if "dimension" in kwargs:
            dimension = kwargs.pop("dimension")
        else:
            dimension = SENETENCETRANSFORMERS_MODEL_DIM_MAP.get(model, 1536)

        self.dim = dimension
        self.model = model

        # Initialize the appropriate client based on parameters
        
        from sentence_transformers import SentenceTransformer

        self.client = SentenceTransformer(model)
        self.is_azure = False

    def _get_dim(self):
        """
        Get the dimension parameter for the API call.

        Returns:
            int or NOT_GIVEN: The dimension to use for the embedding, or NOT_GIVEN
            if using all-MiniLM-L6-v2 which doesn't support custom dimensions.
        """
        return self.dim if self.model != "all-MiniLM-L6-v2" else NOT_GIVEN

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text (str): The query text to embed.

        Returns:
            List[float]: A list of floats representing the embedding vector.
        """
        
        response = self.client.encode(
            [text]
            )

        return response.tolist()
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document texts.

        Args:
            texts (List[str]): A list of document texts to embed.

        Returns:
            List[List[float]]: A list of embedding vectors, one for each input text.
        """

        response = self.client.encode_document(
                input=texts,
            )
        

        return [r.tolist() for r in response]

    @property
    def dimension(self) -> int:
        """
        Get the dimensionality of the embeddings for the current model.

        Returns:
            int: The number of dimensions in the embedding vectors.
        """
        return self.dim
