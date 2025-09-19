from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
import logging
from ..services.kamiwaza_service import KamiwazaService
from ..services.base_service import BaseService, ExampleTextService
from ..core.errors import ValidationError, NotFoundError
from ..models.base import HealthResponse, HealthStatus
from ..models.examples import TextAnalysisRequest

logger = logging.getLogger(__name__)
router = APIRouter()


class TranscriptRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    transcript: str
    model_name: str


class SummaryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    summary: str
    model_used: str


def get_kamiwaza_service() -> KamiwazaService:
    return KamiwazaService()


@router.get("/health", response_model=HealthResponse)
async def health_check(service: KamiwazaService = Depends(get_kamiwaza_service)):
    """
    Enhanced health check endpoint for App Garden.
    
    Checks the health of various components including
    Kamiwaza connection.
    """
    components = {}
    
    # Check Kamiwaza connection
    try:
        models = await service.list_models()
        components["kamiwaza"] = HealthStatus(
            healthy=True,
            message=f"Connected, {len(models)} models available"
        )
    except Exception as e:
        components["kamiwaza"] = HealthStatus(
            healthy=False,
            message=str(e)
        )
    
    # Overall health
    all_healthy = all(c.healthy for c in components.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        service="app-garden-template",
        version="1.0.0",
        components=components
    )


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_models(service: KamiwazaService = Depends(get_kamiwaza_service)):
    """List available AI models from Kamiwaza."""
    try:
        models = await service.list_models()
        return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.post("/summarize", response_model=SummaryResponse)
async def summarize_transcript(
    request: TranscriptRequest,
    service: KamiwazaService = Depends(get_kamiwaza_service)
):
    """Summarize a meeting transcript using the selected model."""
    logger.info(f"Summarize request received for model: {request.model_name}")
    logger.info(f"Transcript length: {len(request.transcript)} characters")
    
    try:
        # Check if we can reach the model endpoint
        models = await service.list_models()
        model_exists = any(m["name"] == request.model_name for m in models)
        
        if not model_exists:
            raise ValueError(f"Model {request.model_name} not found")
        
        # For now, provide a mock summary if model endpoint is not accessible
        # This is a temporary workaround for the template demo
        try:
            # Try to get OpenAI client for the selected model
            client = service.get_openai_client(request.model_name)
            logger.info(f"Got OpenAI client successfully")
            
            # Create the summarization prompt
            prompt = f"""Please provide a concise summary of the following meeting transcript. 
Include key topics discussed, decisions made, and action items.

Transcript:
{request.transcript}

Summary:"""
            
            # Call the model
            logger.info(f"Calling model with prompt of length: {len(prompt)}")
            
            response = client.chat.completions.create(
                model=request.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes meeting transcripts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content
            logger.info(f"Got summary of length: {len(summary)}")
            
        except Exception as api_error:
            logger.warning(f"Model API error (using mock response): {api_error}")
            # Provide a simple extractive summary as fallback
            sentences = request.transcript.split('. ')
            key_points = []
            
            # Extract key information
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in ['discussed', 'agreed', 'will', 'decision', 'action']):
                    key_points.append(sentence)
            
            if key_points:
                summary = "Meeting Summary:\n\n" + "\n• ".join(key_points[:3])
            else:
                # Basic summary
                summary = f"Meeting Summary:\n\nThe meeting covered the following topics: {request.transcript[:100]}..."
            
            summary += f"\n\n[Note: Using simplified summary due to model endpoint connectivity]"
        
        return SummaryResponse(
            summary=summary,
            model_used=request.model_name
        )
        
    except Exception as e:
        logger.error(f"Error summarizing transcript: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to summarize: {str(e)}")


# Example endpoint demonstrating new patterns
@router.post("/analyze-text")
async def analyze_text(
    request: TextAnalysisRequest,
    service: ExampleTextService = Depends(lambda: ExampleTextService(KamiwazaService()))
):
    """
    Example endpoint demonstrating structured AI responses.
    
    This endpoint shows how to use:
    - Pydantic models for request/response
    - Base service pattern
    - Structured AI responses with response_format
    """
    try:
        result = await service.analyze_sentiment(
            text=request.text,
            model_name=request.model_name
        )
        return result
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        # Our error handling middleware will format this appropriately
        raise


@router.post("/upload-example")
async def upload_file_example(
    file: UploadFile = File(..., description="File to process"),
    model_name: str = "default-model"
):
    """
    Example file upload endpoint.
    
    Demonstrates:
    - File upload handling
    - File validation
    - Error handling for files
    """
    # Import here to show it's optional
    from ..services.file_parser import file_parser_factory
    
    try:
        # Read file content
        content = await file.read()
        
        # Get appropriate parser
        parser = file_parser_factory.get_parser(file.filename)
        
        # Parse file
        parsed_content = await parser.parse_file(
            filename=file.filename,
            file_content=content,
            content_type=file.content_type
        )
        
        # Process with AI (example)
        # In real app, you'd have a service for this
        return {
            "filename": file.filename,
            "content_preview": str(parsed_content)[:200] + "...",
            "size": len(content),
            "type": file.content_type
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        # The error will be properly formatted by our middleware
        raise