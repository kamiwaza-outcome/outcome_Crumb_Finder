"""
Base service class for App Garden applications.

This module provides a foundation for services that interact with
Kamiwaza AI models, including the response_format pattern for
structured outputs.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from datetime import datetime

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .kamiwaza_service import KamiwazaService
from ..core.errors import AIModelError, ExternalServiceError

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class BaseService(ABC):
    """
    Abstract base class for services in App Garden applications.
    
    Provides common patterns for:
    - AI model interactions with structured responses
    - Error handling and retries
    - Performance tracking
    - Logging
    """
    
    def __init__(self, kamiwaza_service: KamiwazaService):
        """
        Initialize the service with Kamiwaza integration.
        
        Args:
            kamiwaza_service: Instance of KamiwazaService for AI model access
        """
        self.kamiwaza_service = kamiwaza_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(ExternalServiceError)
    )
    async def call_ai_model(
        self,
        prompt: str,
        model_name: str,
        response_schema: Optional[Type[T]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any] | T:
        """
        Call an AI model with optional structured response format.
        
        This method handles:
        - Structured responses using Pydantic schemas
        - Automatic retries on transient failures
        - Comprehensive error handling
        - Performance tracking
        
        Args:
            prompt: The user prompt to send to the model
            model_name: Name of the Kamiwaza model to use
            response_schema: Optional Pydantic model for structured responses
            system_prompt: Optional system prompt for the model
            temperature: Model temperature (0-1)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters for the model
            
        Returns:
            If response_schema is provided: Instance of the schema
            Otherwise: Dictionary with the raw response
            
        Raises:
            AIModelError: If the model call fails
            ValidationError: If response doesn't match schema
        """
        start_time = datetime.utcnow()
        
        try:
            # Get OpenAI client for the model
            client = self.kamiwaza_service.get_openai_client(model_name)
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Prepare request parameters
            request_params = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            # Add response_format if schema is provided
            if response_schema:
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__.lower(),
                        "strict": True,
                        "schema": response_schema.model_json_schema()
                    }
                }
                
                self.logger.info(
                    f"Calling {model_name} with structured response format: {response_schema.__name__}"
                )
            else:
                self.logger.info(f"Calling {model_name} with unstructured response")
            
            # Make the API call
            response = client.chat.completions.create(**request_params)
            
            # Extract response content
            response_text = response.choices[0].message.content
            
            # Track performance
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(
                f"Model {model_name} responded in {duration:.2f}s",
                extra={
                    "model": model_name,
                    "duration": duration,
                    "tokens_used": response.usage.total_tokens if response.usage else None
                }
            )
            
            # Parse response based on schema
            if response_schema:
                try:
                    # Parse and validate with Pydantic
                    return response_schema.model_validate_json(response_text)
                except ValidationError as e:
                    self.logger.error(f"Response validation failed: {e}")
                    raise AIModelError(
                        model=model_name,
                        message="Response did not match expected schema",
                        details={"validation_errors": e.errors()}
                    )
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON in response: {e}")
                    raise AIModelError(
                        model=model_name,
                        message="Model returned invalid JSON",
                        details={"response": response_text[:200]}
                    )
            else:
                # Return raw response for unstructured calls
                return {
                    "response": response_text,
                    "model": model_name,
                    "usage": response.usage.model_dump() if response.usage else None
                }
        
        except Exception as e:
            # Log the error with context
            self.logger.error(
                f"AI model call failed: {e}",
                exc_info=True,
                extra={
                    "model": model_name,
                    "prompt_length": len(prompt),
                    "has_schema": response_schema is not None
                }
            )
            
            # Convert to appropriate error type
            if isinstance(e, AIModelError):
                raise
            
            # Wrap other exceptions
            raise ExternalServiceError(
                service="Kamiwaza AI",
                message=str(e),
                details={
                    "model": model_name,
                    "error_type": type(e).__name__
                }
            )
    
    async def call_ai_model_simple(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simplified AI model call that returns just the text response.
        
        Args:
            prompt: The user prompt
            model_name: Model to use
            system_prompt: Optional system prompt
            **kwargs: Additional model parameters
            
        Returns:
            The model's text response
        """
        result = await self.call_ai_model(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            **kwargs
        )
        
        return result["response"] if isinstance(result, dict) else str(result)
    
    def build_prompt(self, template: str, **kwargs) -> str:
        """
        Build a prompt from a template with variable substitution.
        
        Args:
            template: Prompt template with {variable} placeholders
            **kwargs: Variables to substitute
            
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"Missing template variable: {e}")
            raise ValueError(f"Prompt template missing required variable: {e}")
    
    @abstractmethod
    async def process(self, *args, **kwargs):
        """
        Main processing method to be implemented by subclasses.
        
        This method should contain the primary business logic
        of the service.
        """
        pass


class ExampleTextService(BaseService):
    """
    Example service showing how to extend BaseService.
    
    This demonstrates using structured responses with the
    response_format pattern.
    """
    
    async def analyze_sentiment(
        self,
        text: str,
        model_name: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of provided text.
        
        Uses the structured response format to ensure consistent output.
        """
        # Import here to avoid circular dependencies
        from ..models.examples import TextAnalysisResult
        
        prompt = self.build_prompt(
            """Analyze the following text and provide:
            1. A brief summary
            2. Sentiment scores (positive, negative, neutral) that sum to 1.0
            3. Key topics (3-5 main topics)
            4. Named entities with their types
            5. Word count
            6. Language code (e.g., 'en' for English)
            
            Text to analyze:
            {text}""",
            text=text
        )
        
        system_prompt = (
            "You are a text analysis expert. Provide detailed analysis "
            "of texts with accurate sentiment scores and entity recognition."
        )
        
        # Call with structured response
        result = await self.call_ai_model(
            prompt=prompt,
            model_name=model_name,
            response_schema=TextAnalysisResult,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        return result.model_dump()
    
    async def process(self, text: str, model_name: str, task: str = "analyze"):
        """
        Process text based on the specified task.
        
        Args:
            text: Input text
            model_name: AI model to use
            task: Task to perform (analyze, summarize, etc.)
        """
        if task == "analyze":
            return await self.analyze_sentiment(text, model_name)
        else:
            raise ValueError(f"Unknown task: {task}")