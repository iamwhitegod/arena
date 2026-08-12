# -----------------------------------------------------------------------------
# Dockerfile for Arena Video Clipping Engine & CLI
# -----------------------------------------------------------------------------

FROM python:3.10-slim-bullseye

# Set environment variables to keep Python and apt-get quiet & efficient
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime system packages: FFmpeg, git, curl, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    git \
    build-essential \
    ca-certificates \
    unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements first (leverage layer cache)
COPY engine/requirements.txt ./engine/requirements.txt
RUN pip install --no-cache-dir -r engine/requirements.txt

# Copy CLI packages first and install Node packages
COPY cli/package*.json ./cli/
RUN cd cli && npm install --ignore-scripts

# Copy source folders
COPY engine/ ./engine/
COPY cli/ ./cli/

# Compile TypeScript CLI and register 'arena' globally
RUN cd cli && npm run build && npm link

# Establish clean mount point for the host workspace
WORKDIR /workspace

ENTRYPOINT ["arena"]
