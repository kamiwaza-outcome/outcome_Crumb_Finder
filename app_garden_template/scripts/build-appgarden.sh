#!/bin/bash
set -e

# Build script for App Garden deployment
# Usage: ./scripts/build-appgarden.sh [version] [docker-org]

# Function to increment version
increment_version() {
    local version=$1
    # Remove 'v' prefix if present
    version=${version#v}
    
    # Split into major.minor.patch
    IFS='.' read -r major minor patch <<< "$version"
    
    # Increment patch version
    patch=$((patch + 1))
    
    echo "v${major}.${minor}.${patch}"
}

# Function to get latest version from app_garden_config directory
get_latest_version() {
    local config_dir="app_garden_config"
    local latest_version="v1.0.0"
    
    if [ -d "$config_dir" ]; then
        # Find all json files and extract versions
        for file in "$config_dir"/${APP_NAME}-appgarden-v*.json; do
            if [ -f "$file" ]; then
                # Extract version from filename
                local filename=$(basename "$file")
                local version=$(echo "$filename" | sed -n 's/.*-appgarden-\(v[0-9.]*\)\.json/\1/p')
                if [ ! -z "$version" ]; then
                    latest_version=$version
                fi
            fi
        done
    fi
    
    echo "$latest_version"
}

APP_NAME="app-garden-template"
DOCKER_ORG=${2:-"kamiwazaai"}

# If no version provided, auto-increment from latest
if [ -z "$1" ]; then
    LATEST_VERSION=$(get_latest_version)
    VERSION=$(increment_version "$LATEST_VERSION")
    echo "Auto-incrementing from $LATEST_VERSION to $VERSION"
else
    VERSION=$1
fi

echo "Building App Garden Template images"
echo "Version: $VERSION"
echo "Docker Organization: $DOCKER_ORG"

# Ensure app_garden_config directory exists
mkdir -p app_garden_config

echo ""

# Ensure docker buildx is available
if ! docker buildx version &> /dev/null; then
    echo "Error: docker buildx is required for multi-arch builds"
    echo "Please install Docker Desktop or enable buildx"
    exit 1
fi

# Create and use a new builder instance if needed
BUILDER_NAME="appgarden-builder"
if ! docker buildx ls | grep -q $BUILDER_NAME; then
    echo "Creating buildx builder..."
    docker buildx create --name $BUILDER_NAME --use
    docker buildx inspect --bootstrap
fi

# Build backend image with multi-arch support
echo "Building backend image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $DOCKER_ORG/${APP_NAME}-backend:$VERSION \
  -t $DOCKER_ORG/${APP_NAME}-backend:latest \
  -f backend/Dockerfile \
  --push \
  ./backend

# Build frontend image with multi-arch support
echo "Building frontend image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $DOCKER_ORG/${APP_NAME}-frontend:$VERSION \
  -t $DOCKER_ORG/${APP_NAME}-frontend:latest \
  -f frontend/Dockerfile \
  --push \
  ./frontend

echo ""
echo "Build complete! Images pushed to Docker Hub:"
echo "  - $DOCKER_ORG/${APP_NAME}-backend:$VERSION"
echo "  - $DOCKER_ORG/${APP_NAME}-frontend:$VERSION"

# Generate App Garden metadata
echo ""
echo "Generating App Garden metadata..."

# Create a temporary compose file with resolved variables
TEMP_COMPOSE=$(mktemp)
cat docker-compose.yml | \
  sed "s/\${DOCKER_REGISTRY:-docker.io}/docker.io/g" | \
  sed "s/\${DOCKER_USERNAME}/$DOCKER_ORG/g" | \
  sed "s/\${VERSION:-latest}/$VERSION/g" > "$TEMP_COMPOSE"

# Read and properly escape the compose content for JSON
COMPOSE_CONTENT=$(python3 -c "
import json
with open('$TEMP_COMPOSE', 'r') as f:
    content = f.read()
print(json.dumps(content))
" | sed 's/^"//;s/"$//')

# Create the App Garden JSON file with version in filename
cat > app_garden_config/${APP_NAME}-appgarden-${VERSION}.json << EOF
{
  "name": "Meeting Transcript Summarizer",
  "version": "${VERSION#v}",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "A simple AI-powered meeting transcript summarizer. Select from available Kamiwaza AI models to generate concise summaries of your meeting transcripts. Perfect template for building App Garden applications.",
  "category": "productivity",
  "tags": ["ai", "transcript", "summarizer", "template", "nextjs", "fastapi"],
  "author": "App Garden Team",
  "homepage": "https://github.com/$DOCKER_ORG/$APP_NAME",
  "compose_yml": "$COMPOSE_CONTENT",
  "risk_tier": 1,
  "verified": false,
  "env_defaults": {
    "KAMIWAZA_ENDPOINT": "http://host.docker.internal:7777/api/",
    "KAMIWAZA_VERIFY_SSL": "false",
    "NODE_TLS_REJECT_UNAUTHORIZED": "0"
  },
  "preferred_model_type": "chat",
  "fail_if_model_type_unavailable": false,
  "preferred_model_name": "qwen3",
  "fail_if_model_name_unavailable": false
}
EOF

rm -f "$TEMP_COMPOSE"

echo "Generated app_garden_config/${APP_NAME}-appgarden-${VERSION}.json"
echo ""
echo "To deploy to App Garden:"
echo "1. Upload app_garden_config/${APP_NAME}-appgarden-${VERSION}.json to the Kamiwaza App Garden"
echo "2. The app will be available for installation"
echo ""
echo "To test locally:"
echo "  docker-compose up"