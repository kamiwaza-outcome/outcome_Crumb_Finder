#!/bin/bash

# Test with Docker Compose using the pushed images

# Set default values
export DOCKER_USERNAME="${DOCKER_USERNAME:-kamiwazaai}"
export VERSION="${VERSION:-latest}"

echo "Testing with Docker images:"
echo "  Backend:  $DOCKER_USERNAME/app-garden-template-backend:$VERSION"
echo "  Frontend: $DOCKER_USERNAME/app-garden-template-frontend:$VERSION"
echo ""

# Run docker compose
docker-compose up "$@"