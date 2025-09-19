# 🚀 Kamiwaza App Garden Template

> A production-ready template with **Kamiwaza SDK pre-integrated** and a **working AI meeting summarizer** showcase app

This template provides everything you need to create AI-powered applications that use **locally deployed models** on your Kamiwaza platform - no cloud API keys needed! It includes the Kamiwaza SDK, UI components, and a complete meeting transcript summarizer as a starting point for your own AI applications.

## 🌟 What is This?

This is a **complete, production-ready template** with the **Kamiwaza SDK pre-integrated** for building applications on the [Kamiwaza App Garden](https://kamiwaza.ai) platform. It includes a **working meeting transcript summarizer** as a showcase example. Think of it as your starter kit for creating AI-powered applications that can:
- Use **locally deployed AI models** running on your Kamiwaza instance (no API keys needed!)
- Process data where it lives (no data movement required)
- Deploy with one click to enterprise environments
- Scale automatically across cloud, on-premises, and edge infrastructure

### What's Kamiwaza?

**Kamiwaza** is an AI orchestration platform that runs AI models locally on your infrastructure. Their platform:
- **Runs models locally** - No cloud API keys needed, models run on your Kamiwaza deployment
- **Hardware agnostic** - Works on Intel, AMD, Nvidia, ARM
- **Enterprise secure** - Your data never leaves your infrastructure

### What's the App Garden?

The **App Garden** is Kamiwaza's marketplace and deployment platform - think of it as an "app store for enterprise AI." It provides:
- One-click deployment of containerized AI applications
- Automatic infrastructure management (no Kubernetes knowledge needed)
- Built-in AI model integration
- Curated marketplace of pre-built applications

## 🎁 What's Included in This Template?

This template comes with:
- ✅ **Kamiwaza SDK pre-integrated** - Ready-to-use Python SDK for AI model access
- ✅ **Meeting Transcript Summarizer** - Working example app showing AI capabilities
- ✅ **Kamiwaza UI Theme** - Professional dark theme with Kamiwaza branding and colors
- ✅ **Production Components** - File upload, modals, toasts, loading states all ready
- ✅ **Docker Configuration** - Pre-configured for App Garden deployment
- ✅ **API Proxy Pattern** - Proper frontend-backend communication setup

## 💡 What Can You Build?

Starting from the included meeting summarizer example, you can build:
- **Document Processing Apps**: Summarize, analyze, extract data from PDFs/Word docs
- **Meeting Tools**: Transcription, summarization, action item extraction
- **Customer Service**: Chatbots, ticket classification, sentiment analysis
- **Data Analysis**: Natural language queries on structured data
- **Content Generation**: Marketing copy, technical documentation, translations
- **Compliance Tools**: Document review, policy checking, audit assistance
- **Any AI-Powered Application**: If it uses AI models, this template can handle it

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Application                         │
├──────────────────┬───────────────────────────────────────────┤
│   Frontend       │              Backend                      │
│   (Next.js)      │             (FastAPI)                     │
│   Port 3000      │             Port 8000                     │
│        ↓         │                 ↓                         │
│   [API Proxy]    │         [Kamiwaza SDK]                   │
│        ↓         │                 ↓                         │
└────────┴─────────┴─────────────────────────────────────────┘
         ↓                           ↓
┌────────────────────────────────────────────────────────────┐
│                  Kamiwaza Platform                          │
│  • AI Model Management (OpenAI, Claude, Llama, etc.)        │
│  • Distributed Processing                                   │
│  • Data Catalog & Vector DB                                 │
│  • Authentication & Security                                │
└────────────────────────────────────────────────────────────┘
```

## 🎯 Key Features

### Pre-Integrated Features

✅ **Kamiwaza SDK** - Complete SDK integration for accessing locally deployed models  
✅ **Model Discovery** - Automatically lists models deployed on your Kamiwaza instance  
✅ **No API Keys** - Uses locally running models, no external services required  
✅ **Meeting Summarizer** - Working showcase app with full UI and backend  
✅ **Kamiwaza Branding** - Logo, colors, and design system pre-configured  
✅ **Production-Ready** - Error handling, retries, logging, monitoring  
✅ **Multi-Architecture** - Works on Intel, AMD, ARM (M1/M2 Macs included)  
✅ **File Processing** - PDF, Word, Excel, CSV, JSON parsing built-in  
✅ **One-Click Deploy** - Automatic App Garden metadata generation  

### What's Included

#### Backend (FastAPI + Python)
- **Kamiwaza SDK Integration**: Complete setup for AI model access
- **Structured AI Responses**: Guaranteed valid JSON outputs using Pydantic
- **File Parser System**: Support for PDF, DOCX, TXT, CSV, JSON, XLSX
- **Error Handling**: Custom exception types with user-friendly messages
- **Retry Logic**: Automatic retries with exponential backoff
- **Health Checks**: App Garden monitoring endpoints
- **CORS Configuration**: Proper cross-origin setup
- **Environment Management**: Pydantic Settings for configuration

#### Frontend (Next.js + React)
- **Kamiwaza UI Theme**: Complete design system with brand colors
- **Component Library**: File upload, modals, toasts, loading states
- **API Client**: Type-safe client with retry logic and interceptors
- **Markdown Rendering**: Beautiful formatting for AI responses
- **Dark Mode Ready**: Automatic theme switching support
- **Responsive Design**: Mobile-first, accessible components
- **Error Boundaries**: Graceful error handling throughout

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop))
- **Python 3.11+** for backend development
- **Node.js 20+** for frontend development
- **Kamiwaza Platform** running locally (get started at [kamiwaza.ai](https://kamiwaza.ai))

### 1. Clone & Setup

```bash
# Clone this template
git clone https://github.com/kamiwazaai/app-garden-template.git my-ai-app
cd my-ai-app

# Remove template git history
rm -rf .git
git init

# Install dependencies
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
```

### 2. Configure Environment

Create `.env` files for local development:

**Backend** (`backend/.env`):
```env
# Point to your local Kamiwaza instance
KAMIWAZA_ENDPOINT=http://localhost:7777/api/
KAMIWAZA_VERIFY_SSL=false

# No API keys needed! Models run locally on Kamiwaza
# Optional: Configure for your environment
PROJECT_NAME=my-ai-app
LOG_LEVEL=INFO
```

**Frontend** (`frontend/.env.local`):
```env
# API connection for local development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Development

Run both services in separate terminals:

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd frontend
npm run dev
```

Visit http://localhost:3000 to see your app!

### 4. Test with Docker

```bash
# Quick test with pre-built images
./scripts/test-docker.sh

# Or build and run your own
docker-compose up --build
```

## 📦 Pre-Integrated Kamiwaza SDK

This template includes the **Kamiwaza SDK fully configured** and ready to use. The SDK connects to your local Kamiwaza instance to access deployed models:

### What's Pre-Configured

```python
# The SDK is already integrated in backend/app/services/kamiwaza_service.py
from kamiwaza_client import KamiwazaClient

# Connects to your local Kamiwaza instance
client = KamiwazaClient("http://localhost:7777/api/")

# 1. List locally deployed models (no cloud required!)
models = await service.list_models()  # Returns models running on YOUR hardware

# 2. Use any model with OpenAI-compatible API
openai_client = service.get_openai_client("llama-3.1-70b")  # Or any deployed model
response = openai_client.chat.completions.create(
    messages=[{"role": "user", "content": "Hello!"}]
)
# This runs on YOUR Kamiwaza instance, not in the cloud!

# 3. Additional SDK capabilities available:
# - Vector Database for RAG applications
# - Data Catalog for managing datasets
# - Model deployment and management
```

### How the Included Summarizer Works

1. **Model Discovery**: Lists models deployed on your Kamiwaza instance
2. **Model Selection**: User picks from available local models
3. **Text Processing**: Sends transcript to selected model running locally
4. **AI Response**: Model generates summary using your compute resources
5. **Display Results**: Formatted with Markdown and Kamiwaza branding

**No external API calls** - Everything runs on your infrastructure!

The template includes this working code:
```python
# backend/app/services/kamiwaza_service.py (pre-integrated)
class KamiwazaService:
    async def list_models(self):
        """Lists models deployed on YOUR Kamiwaza instance."""
        deployments = self._client.serving.list_active_deployments()
        return [{
            "name": d.m_name,
            "status": d.status,
            "endpoint": d.endpoint  # Local endpoint, not cloud!
        }]
```

## 🏗️ Customizing the Template

### Starting Point: Meeting Summarizer

The template includes a **fully working meeting transcript summarizer** that demonstrates:
- Model selection from your Kamiwaza deployment
- Text processing with AI
- Beautiful UI with Kamiwaza theme
- Error handling and loading states

### Step 1: Extend or Replace the Summarizer

Build on top of the included example:

```python
# backend/app/api/routes.py
@router.post("/api/analyze-document")
async def analyze_document(
    file: UploadFile,
    model_name: str,
    service: YourService = Depends()
):
    content = await file.read()
    result = await service.analyze(content, model_name)
    return result
```

### Step 2: Update the UI

```tsx
// frontend/app/page.tsx
export default function YourApp() {
  // Your custom UI components
  return (
    <div>
      <FileUpload onUpload={handleFileUpload} />
      <ModelSelector models={models} />
      <ResultsDisplay results={analysisResults} />
    </div>
  );
}
```

### Step 3: Add Your Business Logic

```python
# backend/app/services/your_service.py
class YourService(BaseService):
    async def process(self, data: dict, model_name: str):
        # Your AI-powered logic here
        client = self.get_openai_client(model_name)
        
        # Use structured outputs for guaranteed format
        result = await self.call_ai_model(
            prompt="Analyze this data...",
            model_name=model_name,
            response_schema=YourResponseModel
        )
        
        return result
```

## 🚢 Deploying to App Garden

### 1. Build & Package

```bash
# This single command does everything!
./scripts/build-appgarden.sh v1.0.0 your-dockerhub-username

# What it does:
# ✓ Builds multi-architecture Docker images (amd64 + arm64)
# ✓ Pushes to Docker Hub
# ✓ Generates App Garden metadata JSON
# ✓ Validates everything is ready
```

## 📊 Advanced Features

### Structured AI Responses

Guarantee your AI returns valid, typed data:

```python
from pydantic import BaseModel
from typing import List

class AnalysisResult(BaseModel):
    summary: str
    sentiment: float  # -1.0 to 1.0
    key_points: List[str]
    action_items: List[dict]

# In your service
result = await self.call_ai_model(
    prompt="Analyze this meeting transcript",
    model_name=model_name,
    response_schema=AnalysisResult  # ← Guarantees this structure!
)

# result is now a validated AnalysisResult instance
print(result.sentiment)  # Guaranteed to be a float
```

### File Processing Pipeline

Handle any file type with built-in parsers:

```python
from app.services.file_parser import file_parser_factory

# Automatic format detection
parser = file_parser_factory.get_parser(filename)
content = await parser.parse_file(filename, file_bytes)

# Supported formats out of the box:
# PDF, DOCX, TXT, MD, CSV, JSON, XLSX
```

### Streaming AI Responses

For real-time AI output:

```python
@router.post("/api/stream")
async def stream_response(request: StreamRequest):
    async def generate():
        async for chunk in ai_service.stream(request):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Background Processing

For long-running tasks:

```python
from fastapi import BackgroundTasks

@router.post("/api/process-async")
async def process_async(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(long_running_task, task_id, request)
    return {"task_id": task_id, "status": "processing"}
```

## 🛠️ Development Tips

### Testing Without Kamiwaza Models

The template includes **mock responses** for development without deployed models:

```python
# Already included in backend/app/api/routes.py
if not openai_client:
    # Fallback mock response when no models are available
    return SummarizeResponse(
        summary="This is a mock summary for development..."
    )
```

For full functionality, deploy models on your Kamiwaza instance.

### Testing Your Application

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test

# End-to-end tests with Docker
./scripts/test-e2e.sh
```

### Performance Optimization

1. **Use streaming for large responses**
2. **Implement caching for repeated queries**
3. **Use background tasks for heavy processing**

## 🐛 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot connect to Kamiwaza" | Ensure Kamiwaza is running locally on port 7777 |
| "No models available" | Deploy models on your Kamiwaza instance first |
| "CORS errors" | Frontend must use `/api` proxy, not direct backend calls |
| "Docker build fails" | Ensure Docker Desktop is running and has enough resources |
| "Port already in use" | Change ports in docker-compose.yml or kill existing processes |

### Debug Mode

Enable detailed logging:

```bash
# Backend
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# Frontend
NEXT_PUBLIC_DEBUG=true npm run dev
```

### Getting Help

- 📚 [Kamiwaza Documentation](https://docs.kamiwaza.ai)
- 💬 [Community Discord](https://discord.gg/kamiwaza)
- 🐛 [Report Issues](https://github.com/kamiwazaai/app-garden-template/issues)
- 📧 [Enterprise Support](mailto:support@kamiwaza.ai)

## 🎓 Learning Resources

### Tutorials
- [Building Your First App Garden Application](https://docs.kamiwaza.ai/tutorials/first-app)
- [Understanding the Kamiwaza SDK](https://docs.kamiwaza.ai/sdk/python)
- [App Garden Deployment Guide](https://docs.kamiwaza.ai/appgarden/deployment)

### Example Applications
- [Document Q&A System](https://github.com/kamiwazaai/examples/tree/main/document-qa)
- [Customer Support Bot](https://github.com/kamiwazaai/examples/tree/main/support-bot)
- [Data Analysis Assistant](https://github.com/kamiwazaai/examples/tree/main/data-assistant)

## 🚀 What's Next?

### Possibilities with This Template

Since all models run locally on your Kamiwaza deployment, you can:
- **Multi-Model Comparison**: Test prompts across different locally deployed models
- **RAG Applications**: Use Kamiwaza's vector database with your private data
- **Agent Systems**: Build workflows without external API dependencies
- **Real-time Processing**: Stream responses from local models
- **Batch Operations**: Process sensitive documents that can't leave your infrastructure

### Scaling Your Application

When your app grows, Kamiwaza handles:
- **Automatic scaling** across multiple nodes
- **Load balancing** between instances
- **Model caching** for performance
- **Request queuing** during high load
- **Failover** to backup models

## 📜 License

This template is provided under the MIT License. Use it to build amazing AI applications!

---

<div align="center">

**Built with ❤️ for the Kamiwaza App Garden ecosystem**

[Get Started](https://kamiwaza.ai) • [Documentation](https://docs.kamiwaza.ai) • [Support](mailto:support@kamiwaza.ai)

</div>