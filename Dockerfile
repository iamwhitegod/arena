# syntax=docker/dockerfile:1.7

# Keep the human-readable tag for maintainers and the digest for reproducibility.
# Dependabot should update both together when the official image is rebuilt.
ARG NODE_IMAGE=node:22.23.2-bookworm-slim@sha256:d649c27dae7ba0137b3cef5dd75baa422c08dc3d9e3fc0c23dfb172dc3cc6436

FROM ${NODE_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INPUT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY engine/build-requirements.txt engine/build-requirements.lock ./engine/
COPY engine/requirements.txt engine/requirements.lock ./engine/

RUN python3 -m venv /opt/arena-venv \
    && /opt/arena-venv/bin/python -m pip install \
        --no-cache-dir \
        --no-build-isolation \
        --require-hashes \
        --requirement engine/build-requirements.lock \
    && /opt/arena-venv/bin/python -m pip install \
        --no-cache-dir \
        --no-build-isolation \
        --require-hashes \
        --requirement engine/requirements.lock

COPY engine/setup.py engine/arena-cli ./engine/
COPY engine/arena ./engine/arena

RUN /opt/arena-venv/bin/python -m pip install \
        --no-cache-dir \
        --no-build-isolation \
        --no-deps \
        ./engine \
    && chmod 0755 engine/arena-cli

COPY cli/package.json cli/package-lock.json ./cli/
RUN npm ci --prefix cli --ignore-scripts

COPY cli/tsconfig.json ./cli/tsconfig.json
COPY cli/scripts/check-node-version.cjs cli/scripts/clean.cjs cli/scripts/postbuild.cjs ./cli/scripts/
COPY cli/src ./cli/src
RUN npm run build --prefix cli \
    && npm prune --prefix cli --omit=dev --ignore-scripts

FROM ${NODE_IMAGE} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    ARENA_HOME=/home/node/.arena \
    HOME=/home/node \
    MPLCONFIGDIR=/tmp/matplotlib \
    NUMBA_CACHE_DIR=/tmp/numba \
    PATH=/opt/arena-venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/tmp/cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsndfile1 \
        python3 \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/arena-venv /opt/arena-venv
COPY --from=builder --chown=node:node /build/cli/dist /opt/arena-cli/dist
COPY --from=builder --chown=node:node /build/cli/node_modules /opt/arena-cli/node_modules
COPY --from=builder --chown=node:node /build/cli/package.json /opt/arena-cli/package.json
COPY --from=builder --chown=node:node /build/engine /opt/arena-cli/engine

RUN mkdir -p /home/node/.arena /workspace \
    && chown -R node:node /home/node/.arena /workspace \
    && ln -s /opt/arena-cli/dist/launcher.js /usr/local/bin/arena

WORKDIR /workspace
USER node

ENTRYPOINT ["tini", "--", "arena"]
CMD ["--help"]
