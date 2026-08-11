#!/usr/bin/env bash

# Exit immediately if a command fails
set -e

# Verify that the Docker daemon is running
if ! docker info >/dev/null 2>&1; then
  echo "❌ Error: Docker daemon is not running. Please start Docker Desktop first." >&2
  exit 1
fi

# Set image name
IMAGE_NAME="whitegodkingsley/arena:latest"

# Build image if it doesn't exist locally
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
  echo "🐋 Docker image '$IMAGE_NAME' not found locally. Building image..."
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
  PROJECT_ROOT="$SCRIPT_DIR/.."
  docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"
  echo "✓ Docker image built successfully!"
fi

# Check for API key in the environment
if [[ -z "$OPENAI_API_KEY" ]]; then
  echo "⚠️  Warning: OPENAI_API_KEY is not defined in your active environment variables."
fi

# Run the Docker container, mounting the host current directory to /workspace
docker run --rm -it \
  -v "$(pwd)":/workspace \
  -w /workspace \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="$OPENAI_BASE_URL" \
  "$IMAGE_NAME" "$@"
