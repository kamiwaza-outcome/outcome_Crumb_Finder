# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Frontend Development
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server with Turbopack (port 3000)
npm run build        # Build production application
npm run lint         # Run Next.js linting
npm run start        # Start production server
```

### Backend Development
```bash
cd backend
pip install -r requirements.txt    # Install dependencies
uvicorn app.main:app --reload --port 8000    # Start development server
```

### Docker & Deployment
```bash
./scripts/test-docker.sh                    # Test full stack with Docker Compose
./scripts/build-appgarden.sh 1.0.0 myorg    # Build multi-arch images and generate App Garden metadata
docker-compose up                           # Run full stack locally
```

## Architecture

### API Communication Pattern
The frontend and backend communicate through a **proxy pattern**:
1. Frontend makes requests to `/api/*` endpoints
2. Next.js API route handler at `frontend/app/api/[...path]/route.ts` proxies to backend
3. Backend receives requests at `http://backend:8000`
4. This pattern works in both development and App Garden deployment

### Key Service Integration
- **Backend → Kamiwaza**: Uses `host.docker.internal` when running in Docker
- **Configuration**: Backend uses Pydantic Settings (`backend/app/core/config.py`)
- **API Client**: Frontend uses typed client (`frontend/lib/api.ts`)

### App Garden Deployment Requirements
- No host port specifications in docker-compose.yml (App Garden assigns ports)
- Multi-architecture Docker builds (amd64/arm64) required
- Health check endpoint at `/api/health` must be implemented
- Uses standalone Next.js output for minimal container size
- Non-root users in containers (`nextjs` for frontend, `appuser` for backend)

### Project Structure
- **Frontend**: Next.js 15 with App Router, TypeScript, Tailwind CSS
- **Backend**: FastAPI with Kamiwaza SDK integration
- **API Endpoints**:
  - `/api/health` - Health check
  - `/api/models` - List available Kamiwaza models
  - `/api/summarize` - Process meeting transcripts

When modifying this codebase, ensure compatibility with App Garden deployment requirements and maintain the proxy pattern for API communication.