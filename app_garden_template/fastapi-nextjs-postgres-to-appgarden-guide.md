# Converting FastAPI + Next.js + PostgreSQL Apps to App Garden

This guide walks through converting a typical three-tier web application (FastAPI backend, Next.js frontend, PostgreSQL database) into an App Garden-compatible application.

## Table of Contents
1. [Overview](#overview)
2. [Docker Configuration](#docker-configuration)
3. [Docker Compose Requirements](#docker-compose-requirements)
4. [Environment Variables](#environment-variables)
5. [App Garden Metadata](#app-garden-metadata)
6. [Build and Deployment](#build-and-deployment)
7. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
8. [Testing Your App](#testing-your-app)

## Overview

App Garden is Kamiwaza's application deployment platform that provides:
- Automatic port allocation
- AI model integration
- Simplified deployment
- Environment management

Key requirements:
- Multi-architecture Docker images (amd64/arm64)
- No host port specifications in docker-compose
- Support for Kamiwaza environment variables
- Proper metadata configuration
- API proxy for frontend-to-backend communication
- Use `host.docker.internal` for Kamiwaza platform access

## Docker Configuration

### Backend Dockerfile (FastAPI)

Create `backend/Dockerfile.appgarden`:

```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user (required for App Garden)
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Update PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Use standard port 8000 for FastAPI
EXPOSE 8000

# Start command with proper host binding
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile (Next.js)

Create `frontend/Dockerfile.appgarden`:

```dockerfile
# Multi-stage build
FROM node:20-slim AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build with standalone output for smaller images
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production stage
FROM node:20-slim AS runner
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1001 nextjs

# Copy built application
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs

# Standard Next.js port
EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

CMD ["node", "server.js"]
```

### Important Notes:
- Always use multi-stage builds to reduce image size
- Create and use non-root users (security requirement)
- Use standard ports (8000 for FastAPI, 3000 for Next.js)
- Ensure proper permissions with `--chown`

## Docker Compose Requirements

Create `docker-compose.appgarden.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    # CRITICAL: Never specify ports section!
    # ports:
    #   - "5432:5432"  # ❌ DO NOT DO THIS
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-myapp}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-myapp}
      POSTGRES_DB: ${POSTGRES_DB:-myapp}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-myapp}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    image: ${DOCKER_REGISTRY:-docker.io}/${DOCKER_USERNAME}/myapp-backend:${VERSION:-latest}
    # NO ports section - only expose the container port
    ports:
      - "8000"  # Container port only - App Garden allocates host port
    # CRITICAL: Add this for host.docker.internal to work
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      db:
        condition: service_healthy
    environment:
      # Database
      DATABASE_URL: postgresql://${POSTGRES_USER:-myapp}:${POSTGRES_PASSWORD:-myapp}@db:5432/${POSTGRES_DB:-myapp}
      
      # Kamiwaza Model Endpoint - use host.docker.internal
      KAMIWAZA_ENDPOINT: ${KAMIWAZA_ENDPOINT:-http://host.docker.internal:7777/api/}
      KAMIWAZA_VERIFY_SSL: ${KAMIWAZA_VERIFY_SSL:-false}
      
      # Kamiwaza Platform Integration
      KAMIWAZA_API_URI: ${KAMIWAZA_API_URI:-https://host.docker.internal/api}
      KAMIWAZA_FORCE_HTTP: ${KAMIWAZA_FORCE_HTTP:-true}
      NODE_TLS_REJECT_UNAUTHORIZED: ${NODE_TLS_REJECT_UNAUTHORIZED:-0}
      
      # Your app config
      SECRET_KEY: ${SECRET_KEY:-your-secret-key}
      ENVIRONMENT: ${ENVIRONMENT:-production}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    image: ${DOCKER_REGISTRY:-docker.io}/${DOCKER_USERNAME}/myapp-frontend:${VERSION:-latest}
    # NO ports section - only expose the container port
    ports:
      - "3000"  # Container port only - App Garden allocates host port
    depends_on:
      backend:
        condition: service_healthy
    environment:
      # CRITICAL: Backend URL for the API proxy
      BACKEND_URL: http://backend:8000
      
      # SSL/TLS for Node.js
      NODE_TLS_REJECT_UNAUTHORIZED: ${NODE_TLS_REJECT_UNAUTHORIZED:-0}

volumes:
  postgres_data:

# Optional: Add networks for isolation
networks:
  default:
    name: myapp_network
```

### Critical Docker Compose Rules:

1. **Port Configuration**: 
   - Use `ports: ["8000"]` format (container port only)
   - Never use `"8000:8000"` format (host:container mapping)
   - App Garden automatically allocates host ports in the 51100-51193 range

2. **Host Communication**:
   - Add `extra_hosts: ["host.docker.internal:host-gateway"]` to backend service
   - Use `host.docker.internal` for accessing Kamiwaza platform services

3. **Service Communication**:
   - Use Docker service names for internal communication (e.g., `http://backend:8000`)
   - Frontend must proxy API calls - direct browser-to-backend won't work

4. **Health Checks**: Include for proper startup sequencing

5. **Environment Variables**: Support all Kamiwaza platform variables

## Environment Variables

### Required Kamiwaza Variables

Your app must handle these environment variables:

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:pass@localhost/db"
    
    # App Garden / Kamiwaza Integration
    openai_base_url: str = Field(
        default="http://localhost:80",
        alias="OPENAI_BASE_URL"
    )
    openai_api_key: str = Field(
        default="not-needed-kamiwaza",
        alias="OPENAI_API_KEY"
    )
    
    # Support both OPENAI_BASE_URL and OPENAI_BASE_URI
    @validator("openai_base_url", pre=True)
    def validate_openai_url(cls, v, values):
        base_uri = os.getenv("OPENAI_BASE_URI")
        if base_uri and not v:
            return base_uri
        return v
    
    # Kamiwaza Platform
    kamiwaza_api_uri: str = "http://localhost:80"
    kamiwaza_force_http: bool = True
    
    # SSL/TLS
    node_tls_reject_unauthorized: str = "0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Frontend API Proxy (REQUIRED)

App Garden requires frontend-to-backend communication to go through a proxy since direct browser-to-backend connections won't work with dynamic port allocation.

Create `frontend/app/api/[...path]/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';

// Backend URL from environment or Docker service name
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

// Headers to exclude when forwarding
const EXCLUDED_HEADERS = new Set([
  'host', 'connection', 'content-length', 'transfer-encoding',
  'upgrade', 'http2-settings', 'te', 'trailer',
]);

async function handler(request: NextRequest, method: string) {
  try {
    // Build target URL
    const pathSegments = request.nextUrl.pathname.split('/').slice(2); // Remove /api
    const path = pathSegments.join('/');
    const queryString = request.nextUrl.search;
    const targetUrl = `${BACKEND_URL}/${path}${queryString}`;
    
    // Forward headers
    const headers: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
        headers[key] = value;
      }
    });
    
    // Prepare fetch options
    const fetchOptions: RequestInit = {
      method,
      headers,
      cache: 'no-store',
    };
    
    // Add body for methods that support it
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      const contentType = request.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        fetchOptions.body = JSON.stringify(await request.json());
      } else {
        fetchOptions.body = request.body;
      }
      // @ts-expect-error - duplex required by Next.js
      fetchOptions.duplex = 'half';
    }
    
    // Make request to backend
    const response = await fetch(targetUrl, fetchOptions);
    
    // Handle streaming responses (SSE for chat, etc.)
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream')) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }
    
    // Handle normal responses
    if (response.status === 204) {
      return new Response(null, { status: 204 });
    }
    
    const data = await response.arrayBuffer();
    return new NextResponse(data, {
      status: response.status,
      headers: Object.fromEntries(response.headers),
    });
  } catch (error) {
    console.error(`[API Proxy] Error:`, error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

// Export handlers for each HTTP method
export async function GET(req: NextRequest) { return handler(req, 'GET'); }
export async function POST(req: NextRequest) { return handler(req, 'POST'); }
export async function PUT(req: NextRequest) { return handler(req, 'PUT'); }
export async function DELETE(req: NextRequest) { return handler(req, 'DELETE'); }
export async function PATCH(req: NextRequest) { return handler(req, 'PATCH'); }
```

Update your API client to use the proxy:

```typescript
// frontend/lib/apiClient.ts

// Dynamically determine API base URL
const getApiBaseUrl = () => {
  // Check for explicit API URL (for local development)
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // In App Garden, ALWAYS use the proxy route
  // This is critical - don't try to determine the backend host!
  return '/api';
};

export const API_BASE = getApiBaseUrl();

// Use in your fetch calls
export async function fetchAPI(endpoint: string, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(), // Your auth logic
    },
    ...options,
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return response.json();
}
```

**Important**: In App Garden, you cannot determine the backend host from the frontend because:
- The backend port is dynamically allocated
- Direct browser-to-backend connections are not possible
- All API calls must go through the frontend's proxy route

## App Garden Metadata

Create `myapp-appgarden.json`:

```json
{
  "name": "My App",
  "version": "1.0.0",
  "description": "FastAPI + Next.js application with PostgreSQL",
  "category": "Productivity",
  "tags": ["fastapi", "nextjs", "postgresql", "ai"],
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/yourusername/myapp",
  "repository": "https://github.com/yourusername/myapp",
  "compose_file": "docker-compose.appgarden.yml",
  "env_defaults": {
    "POSTGRES_USER": "myapp",
    "POSTGRES_PASSWORD": "myapp",
    "POSTGRES_DB": "myapp",
    "SECRET_KEY": "change-me-in-production",
    "ENVIRONMENT": "production"
  },
  "env_descriptions": {
    "POSTGRES_USER": "PostgreSQL username",
    "POSTGRES_PASSWORD": "PostgreSQL password",
    "POSTGRES_DB": "PostgreSQL database name",
    "SECRET_KEY": "Application secret key for JWT/sessions"
  },
  "ai_models": {
    "model_type": "chat",
    "default_model": "claude-3-5-sonnet-20241022"
  },
  "icon": "🚀"
}
```

## Build and Deployment

Create `scripts/build-appgarden.sh`:

```bash
#!/bin/bash
set -e

# Configuration
DOCKER_USERNAME="yourusername"
VERSION="1.0.0"
APP_NAME="myapp"

# Build multi-architecture images
echo "Building backend image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t ${DOCKER_USERNAME}/${APP_NAME}-backend:${VERSION} \
  -t ${DOCKER_USERNAME}/${APP_NAME}-backend:latest \
  -f backend/Dockerfile.appgarden \
  ./backend

echo "Building frontend image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t ${DOCKER_USERNAME}/${APP_NAME}-frontend:${VERSION} \
  -t ${DOCKER_USERNAME}/${APP_NAME}-frontend:latest \
  -f frontend/Dockerfile.appgarden \
  ./frontend

echo "Images pushed successfully!"
echo "Update your docker-compose.appgarden.yml with:"
echo "  Backend: ${DOCKER_USERNAME}/${APP_NAME}-backend:${VERSION}"
echo "  Frontend: ${DOCKER_USERNAME}/${APP_NAME}-frontend:${VERSION}"
```

Make it executable: `chmod +x scripts/build-appgarden.sh`

## Common Pitfalls & Solutions

### 1. Port Configuration Errors

❌ **Wrong:**
```yaml
services:
  backend:
    ports:
      - "8000:8000"  # This will cause deployment failure
```

✅ **Correct:**
```yaml
services:
  backend:
    # No ports section - App Garden handles this
    expose:
      - 8000  # Optional, for documentation
```

### 2. API Communication Issues

❌ **Wrong:**
```javascript
// Hardcoded URLs
fetch('http://localhost:8000/api/data')
```

✅ **Correct:**
```javascript
// Use relative URLs or environment variables
fetch('/api/data')  // Goes through App Garden proxy
```

### 3. Database Connection String

❌ **Wrong:**
```python
DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
```

✅ **Correct:**
```python
DATABASE_URL = "postgresql://user:pass@db:5432/db"  # Use service name
```

### 4. Backend Port Configuration

By default, App Garden expects backend services on port 8000:

❌ **Wrong:**
```python
# Using non-standard port
uvicorn.run(app, host="0.0.0.0", port=6105)
```

✅ **Correct:**
```python
# Use standard port 8000
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 5. Missing Health Checks

Always include health checks for proper startup sequencing:

```python
# backend/app/main.py
@app.get("/health")
async def health_check():
    # Check database connection
    try:
        # Your DB check logic
        return {"status": "healthy"}
    except Exception:
        raise HTTPException(status_code=503, detail="Service unhealthy")
```

### 6. Kamiwaza Platform Access

Always use `host.docker.internal` for accessing Kamiwaza services:

❌ **Wrong:**
```python
KAMIWAZA_ENDPOINT = "http://localhost:7777/api/"
```

✅ **Correct:**
```python
KAMIWAZA_ENDPOINT = "http://host.docker.internal:7777/api/"
```

### 7. Missing API Proxy

The frontend MUST implement an API proxy route - Next.js rewrites alone won't work:

❌ **Wrong (rewrites only):**
```javascript
// next.config.js - This alone is insufficient!
module.exports = {
  async rewrites() {
    return [{
      source: '/api/:path*',
      destination: 'http://backend:8000/:path*',
    }];
  },
};
```

✅ **Correct:**
Implement the full catch-all API route as shown in the Frontend API Proxy section above.

## Testing Your App

### Local Testing with App Garden Environment

```bash
# Test with App Garden-like environment
docker-compose -f docker-compose.appgarden.yml up

# App will be available at:
# - Frontend: http://localhost:<allocated-port>
# - Backend: http://localhost:<allocated-port>
# - Database: Internal only (no external port)
```

### Pre-deployment Checklist

- [ ] Multi-architecture images built (amd64/arm64)
- [ ] No host ports in docker-compose.yml
- [ ] Non-root users in Dockerfiles
- [ ] Environment variable support for Kamiwaza
- [ ] Health checks implemented
- [ ] API communication uses service names
- [ ] Images pushed to public registry
- [ ] Metadata JSON file created
- [ ] Frontend handles relative API URLs

## Key Differences from Standard Docker Deployment

When converting your app for App Garden, these are the critical changes:

1. **Port Mapping**: Use container-only ports (`ports: ["8000"]`), not host:container mapping
2. **API Proxy**: Frontend must implement a catch-all proxy route - direct browser-to-backend won't work
3. **Host Access**: Add `extra_hosts` and use `host.docker.internal` for Kamiwaza services
4. **Standard Ports**: Use 8000 for FastAPI (not custom ports like 6105)
5. **Environment Variables**: Support Kamiwaza platform variables (KAMIWAZA_API_URI, etc.)
6. **No Local Files**: Remove any local file dependencies (configs, MCP servers, etc.)

## Additional Resources

- [App Garden Documentation](https://docs.kamiwaza.ai/app-garden)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-arch Builds](https://docs.docker.com/buildx/working-with-buildx/)

---

*This guide covers the essential steps for converting a typical FastAPI + Next.js + PostgreSQL application to be App Garden compatible. Based on the Kaizen implementation experience.*