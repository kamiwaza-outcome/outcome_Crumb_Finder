# App Garden Template Guide

This guide will help you transform this template into your own App Garden application. The template includes best practices, reusable components, and patterns learned from building production App Garden applications.

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the template
git clone https://github.com/your-org/app-garden-template.git my-app
cd my-app

# Remove git history and start fresh
rm -rf .git
git init

# Install dependencies
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
```

### 2. Configure Your App

Update these files with your application details:

- `backend/app/core/config.py` - Change PROJECT_NAME
- `docker-compose.yml` - Update image names
- `scripts/build-appgarden.sh` - Update APP_NAME
- Update this README with your app's documentation

### 3. Start Development

```bash
# Backend (in one terminal)
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
npm run dev
```

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Core utilities (config, errors)
│   │   ├── middleware/       # Global middleware
│   │   ├── models/           # Pydantic models
│   │   └── services/         # Business logic
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js app directory
│   ├── components/           # Reusable UI components
│   ├── lib/                  # Utilities and API client
│   └── styles/              # Global styles and theme
└── scripts/                  # Build and deployment scripts
```

## 🎯 Key Features

### Backend Features

#### 1. **Pydantic Models with response_format**

The template uses OpenAI's `response_format` parameter for guaranteed structured outputs:

```python
from app.models.base import BaseResponse
from app.services.base_service import BaseService

class MyService(BaseService):
    async def process_data(self, input_text: str, model_name: str):
        # Define your response schema
        from pydantic import BaseModel
        
        class AnalysisResult(BaseModel):
            summary: str
            sentiment: float
            keywords: List[str]
        
        # Call AI with structured response
        result = await self.call_ai_model(
            prompt="Analyze this text...",
            model_name=model_name,
            response_schema=AnalysisResult  # ← Ensures valid JSON
        )
        
        return result  # Already validated!
```

#### 2. **Comprehensive Error Handling**

Custom error types with user-friendly messages:

```python
from app.core.errors import ValidationError, NotFoundError

# Raise errors with context
raise ValidationError(
    message="Invalid file format",
    field="document",
    details={"allowed_types": [".pdf", ".docx"]}
)

# Errors are automatically formatted as JSON responses
```

#### 3. **File Parsing Framework**

Support for multiple file formats out of the box:

```python
from app.services.file_parser import file_parser_factory

# Parse any supported file
parser = file_parser_factory.get_parser("document.pdf")
content = await parser.parse_file("document.pdf", file_bytes)
```

Supported formats: PDF, DOCX, TXT, MD, CSV, JSON, XLSX (with optional dependencies)

#### 4. **Base Service Pattern**

Reusable service base class with AI integration:

```python
class MyService(BaseService):
    async def process(self, data: dict):
        # Automatic retry logic
        # Performance tracking
        # Error handling
        # All built-in!
```

### Frontend Features

#### 1. **File Upload Component**

Drag-and-drop file upload with validation:

```tsx
import { FileUpload } from '@/components/ui/file-upload';

<FileUpload
  label="Upload Document"
  file={selectedFile}
  onFileSelect={setSelectedFile}
  onFileRemove={() => setSelectedFile(null)}
  accept={{
    'application/pdf': ['.pdf'],
    'text/plain': ['.txt']
  }}
  maxSize={10 * 1024 * 1024} // 10MB
/>
```

#### 2. **Loading States**

Multiple loading components for different use cases:

```tsx
import { Spinner, LoadingOverlay, Skeleton } from '@/components/ui/loading-states';

// Simple spinner
<Spinner size="lg" />

// Full page loading
<LoadingOverlay message="Processing..." />

// Content placeholder
<Skeleton width="200px" height="20px" />
```

#### 3. **Modal System**

Flexible modal component:

```tsx
import { Modal, ConfirmModal } from '@/components/ui/modal';

<Modal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  title="Edit Settings"
  footer={<button>Save</button>}
>
  <SettingsForm />
</Modal>
```

#### 4. **Toast Notifications**

Global toast system:

```tsx
import { useToast } from '@/components/ui/toast';

const { showToast } = useToast();

showToast({
  type: 'success',
  title: 'Saved!',
  message: 'Your changes have been saved.'
});
```

#### 5. **Enhanced API Client**

Advanced API client with retry logic and interceptors:

```tsx
import { apiClient } from '@/lib/api-client';

// Add auth header
apiClient.interceptors.request.use((config) => {
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Make requests with automatic retry
const { data } = await apiClient.get('/api/data');
```

## 🎨 Theming

The template includes a comprehensive Kamiwaza theme system:

### CSS Variables

All colors, spacing, and typography are defined as CSS variables in `frontend/styles/theme.css`:

```css
/* Use Kamiwaza brand colors */
.primary-button {
  background-color: var(--kamiwaza-green);
  color: white;
}

/* Automatic dark mode support */
.card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
}
```

### Dark Mode

Dark mode is automatically supported. Toggle by adding/removing the `dark` class on the root element.

## 🔧 Common Patterns

### Adding a New API Endpoint

1. **Define Pydantic models** in `backend/app/models/`:

```python
# backend/app/models/my_feature.py
from pydantic import BaseModel

class MyRequest(BaseModel):
    input_data: str
    options: dict

class MyResponse(BaseModel):
    result: str
    confidence: float
```

2. **Create service** in `backend/app/services/`:

```python
# backend/app/services/my_service.py
from app.services.base_service import BaseService

class MyFeatureService(BaseService):
    async def process(self, request: MyRequest) -> MyResponse:
        # Your business logic here
        pass
```

3. **Add route** in `backend/app/api/routes.py`:

```python
@router.post("/my-feature", response_model=MyResponse)
async def my_feature_endpoint(
    request: MyRequest,
    service: MyFeatureService = Depends()
):
    return await service.process(request)
```

4. **Update frontend** API client:

```typescript
// frontend/lib/api.ts
export async function callMyFeature(data: MyRequest): Promise<MyResponse> {
  return apiClient.post('/api/my-feature', data);
}
```

### Handling File Uploads

Backend:

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    service: MyService = Depends()
):
    # Validate file
    content = await file.read()
    parser = file_parser_factory.get_parser(file.filename)
    parsed = await parser.parse_file(file.filename, content)
    
    # Process
    return await service.process(parsed)
```

Frontend:

```tsx
const handleUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const { data } = await apiClient.upload('/api/upload', formData);
};
```

### Error Handling

Backend errors are automatically formatted. On the frontend:

```tsx
try {
  const data = await apiClient.get('/api/data');
} catch (error) {
  if (error instanceof ApiError) {
    showToast({
      type: 'error',
      title: 'Error',
      message: error.message
    });
  }
}
```

## 🚢 Deployment

### Build for App Garden

```bash
# Build multi-arch images and generate metadata
./scripts/build-appgarden.sh v1.0.0 yourdockerhub

# This creates:
# - Docker images pushed to your registry
# - app-garden-metadata.json for deployment
```

### Environment Variables

Configure in App Garden UI or `.env` files:

```env
# Backend
KAMIWAZA_ENDPOINT=http://host.docker.internal:7777/api/
KAMIWAZA_VERIFY_SSL=false

# Frontend (if needed)
NEXT_PUBLIC_API_URL=/api
```

## 📚 Advanced Topics

### Custom File Parsers

Add support for new file types:

```python
from app.services.file_parser import BaseFileParser

class MyFormatParser(BaseFileParser):
    SUPPORTED_EXTENSIONS = ['.myformat']
    
    async def parse(self, content: bytes, file_info: FileInfo):
        # Parse your format
        return parsed_data

# Register it
file_parser_factory.register_parser('.myformat', MyFormatParser)
```

### Streaming Responses

For AI streaming:

```python
from fastapi.responses import StreamingResponse

@router.post("/stream")
async def stream_response():
    async def generate():
        async for chunk in ai_stream():
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Background Tasks

For long-running operations:

```python
from fastapi import BackgroundTasks

@router.post("/process")
async def process_async(
    background_tasks: BackgroundTasks,
    request: ProcessRequest
):
    background_tasks.add_task(long_running_task, request)
    return {"status": "processing", "id": task_id}
```

## 🐛 Troubleshooting

### Common Issues

1. **"Cannot find module" errors**: Run `npm install` in frontend directory
2. **"Import error" in backend**: Install optional dependencies from requirements.txt
3. **CORS errors**: Check `BACKEND_CORS_ORIGINS` in backend config
4. **File upload fails**: Check file size limits and supported types

### Debug Mode

Enable detailed logging:

```python
# backend/.env
LOG_LEVEL=DEBUG
```

```typescript
// frontend/.env.local
NEXT_PUBLIC_DEBUG=true
```

## 🤝 Contributing

When adding new features to the template:

1. Follow existing patterns
2. Add comprehensive JSDoc/docstrings
3. Update this guide
4. Test with Docker build

## 📝 License

This template is provided as-is for building App Garden applications.