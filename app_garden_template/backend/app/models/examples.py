"""
Example models demonstrating App Garden patterns including response_format usage.

These models show best practices for structuring AI responses and common
application patterns.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .base import TimestampedModel, BaseResponse


# Example: Text Processing Models
class TextAnalysisRequest(BaseModel):
    """Request model for text analysis."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze")
    model_name: str = Field(..., description="AI model to use")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Analysis options")


class SentimentScore(BaseModel):
    """Sentiment analysis scores."""
    positive: float = Field(..., ge=0, le=1, description="Positive sentiment score")
    negative: float = Field(..., ge=0, le=1, description="Negative sentiment score")
    neutral: float = Field(..., ge=0, le=1, description="Neutral sentiment score")


class TextAnalysisResult(BaseModel):
    """
    Structured result for text analysis.
    This model is designed to work with OpenAI's response_format parameter.
    """
    summary: str = Field(..., description="Brief summary of the text")
    sentiment: SentimentScore = Field(..., description="Sentiment analysis scores")
    key_topics: List[str] = Field(..., description="Main topics identified in the text")
    entities: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="Named entities found (name, type pairs)"
    )
    word_count: int = Field(..., description="Total word count")
    language: str = Field(..., description="Detected language code")


# Example: Question-Answer Models
class Question(BaseModel):
    """A single question with metadata."""
    question: str = Field(..., description="The question text")
    category: str = Field(..., description="Question category")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$", description="Difficulty level")
    hints: List[str] = Field(default_factory=list, description="Optional hints")


class QuestionGenerationRequest(BaseModel):
    """Request to generate questions."""
    topic: str = Field(..., description="Topic for questions")
    count: int = Field(5, ge=1, le=20, description="Number of questions to generate")
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard|mixed)$")
    model_name: str = Field(..., description="AI model to use")


class QuestionGenerationResult(BaseModel):
    """
    Structured result for question generation.
    Designed for use with response_format to ensure valid JSON from AI.
    """
    questions: List[Question] = Field(..., description="Generated questions")
    topic_summary: str = Field(..., description="Brief summary of the topic")
    total_generated: int = Field(..., description="Number of questions generated")


# Example: Document Processing Models
class DocumentSection(BaseModel):
    """A section within a document."""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(..., ge=1, le=6, description="Heading level")
    word_count: int = Field(..., description="Words in this section")


class DocumentAnalysis(BaseModel):
    """
    Comprehensive document analysis result.
    Shows how to structure complex nested data for AI responses.
    """
    title: str = Field(..., description="Document title")
    author: Optional[str] = Field(None, description="Document author if available")
    summary: str = Field(..., description="Executive summary")
    sections: List[DocumentSection] = Field(..., description="Document sections")
    key_points: List[str] = Field(..., description="Main takeaways")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Example: Multi-Model Comparison
class ModelComparison(BaseModel):
    """Compare outputs from multiple AI models."""
    model_name: str = Field(..., description="Model that generated this response")
    response: str = Field(..., description="Model's response")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    processing_time: float = Field(..., description="Time taken in seconds")


class ComparisonRequest(BaseModel):
    """Request to compare multiple models."""
    prompt: str = Field(..., description="Prompt to send to all models")
    models: List[str] = Field(..., min_items=2, description="Models to compare")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ComparisonResult(BaseResponse):
    """Result of multi-model comparison."""
    comparisons: List[ModelComparison] = Field(..., description="Individual model results")
    best_model: str = Field(..., description="Recommended model based on criteria")
    analysis: str = Field(..., description="Comparative analysis")


# Example: Streaming Response Models
class StreamEvent(BaseModel):
    """Event in a streaming response."""
    event_type: str = Field(..., description="Type of event")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: float = Field(..., description="Unix timestamp")


class StreamMetadata(BaseModel):
    """Metadata for a streaming session."""
    session_id: str = Field(..., description="Unique session identifier")
    total_events: int = Field(..., description="Total events in stream")
    duration: float = Field(..., description="Stream duration in seconds")


# Example: Batch Processing Models
class BatchItem(BaseModel):
    """Single item in a batch."""
    id: str = Field(..., description="Unique item identifier")
    data: Dict[str, Any] = Field(..., description="Item data to process")
    priority: int = Field(0, ge=0, le=10, description="Processing priority")


class BatchRequest(BaseModel):
    """Request for batch processing."""
    items: List[BatchItem] = Field(..., max_items=100, description="Items to process")
    model_name: str = Field(..., description="AI model to use")
    parallel: bool = Field(False, description="Process items in parallel")


class BatchResult(TimestampedModel):
    """Result of batch processing."""
    batch_id: str = Field(..., description="Unique batch identifier")
    processed: int = Field(..., description="Number of items processed")
    failed: int = Field(..., description="Number of failed items")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Processing errors")