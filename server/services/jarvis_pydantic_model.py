import os
from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

class JarvisPydanticModel(OpenAIModel):
    """
    A PydanticAI-compatible model that connects to the Jarvis AI Server.
    Mirroring the configuration logic of ChatAIServer but for PydanticAI agents.
    """
    def __init__(
        self,
        model_name: str = "qwen3:latest",
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        **kwargs
    ):
        # Resolve configuration from args or env vars
        server_url = server_url or os.getenv("JARVIS_SERVER_URL", "http://localhost:8080")
        auth_token = auth_token or os.getenv("JARVIS_AUTH_TOKEN", "dummy_token")

        # Ensure correct API endpoint suffix for OpenAI compatibility
        base_url = server_url.rstrip("/")
        if not base_url.endswith("/api/v1"):
            base_url = f"{base_url}/api/v1"

        # Create the provider with the custom configuration
        provider = OpenAIProvider(
            base_url=base_url,
            api_key=auth_token
        )

        # Initialize OpenAIModel with the custom provider
        super().__init__(
            model_name=model_name,
            provider=provider,
            **kwargs
        )

# Factory for convenience
def create_pydantic_model(
    model: str = "qwen3:latest",
    server_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    **kwargs
) -> JarvisPydanticModel:
    return JarvisPydanticModel(
        model_name=model,
        server_url=server_url,
        auth_token=auth_token,
        **kwargs
    )
