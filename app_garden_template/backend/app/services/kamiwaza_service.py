from functools import cached_property
from typing import List, Dict, Any
import logging
from kamiwaza_client import KamiwazaClient
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class KamiwazaService:
    """Simple wrapper around kamiwaza_client for model management."""
    
    def __init__(self):
        settings = get_settings()
        self._endpoint = settings.KAMIWAZA_ENDPOINT
        self._verify_ssl = settings.KAMIWAZA_VERIFY_SSL
    
    @cached_property
    def _client(self) -> KamiwazaClient:
        client = KamiwazaClient(self._endpoint)
        client.session.verify = self._verify_ssl
        return client
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available AI models from Kamiwaza."""
        try:
            deployments = self._client.serving.list_active_deployments()
            logger.info(f"Found {len(deployments)} active deployments")
            
            models = []
            for d in deployments:
                models.append({
                    "id": str(d.id),
                    "name": d.m_name,
                    "status": d.status,
                    "endpoint": d.endpoint,
                })
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise
    
    def get_openai_client(self, model_name: str):
        """Get OpenAI-compatible client for the specified model."""
        logger.info(f"Getting OpenAI client for model: {model_name}")
        return self._client.openai.get_client(model_name)