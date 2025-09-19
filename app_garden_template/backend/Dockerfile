FROM python:3.11-slim

# Install git for pip and curl for healthcheck
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser app ./app

# Switch to non-root user
USER appuser

# Use standard port 8000
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]