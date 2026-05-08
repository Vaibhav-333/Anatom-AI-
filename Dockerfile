# Anatom AI — Phase 5 Docker image
# Multi-stage build: deps layer cached separately from source.
#
# Build:
#   docker build -t anatomai:latest .
#
# Run API server:
#   docker run -p 8000:8000 anatomai:latest
#
# Run dashboard:
#   docker run -p 8501:8501 anatomai:latest streamlit run src/ui/app.py --server.port 8501

FROM python:3.12-slim AS base

# System dependencies for OpenCV, SimpleITK, matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------------------------------------------------------
# Dependency layer (cached unless requirements.txt changes)
# ---------------------------------------------------------------------------
FROM base AS deps

COPY requirements.txt .

# Upgrade pip quietly and install all project dependencies
RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Runtime image
# ---------------------------------------------------------------------------
FROM deps AS runtime

# Copy only source (no data, no checkpoints)
COPY src/      ./src/
COPY scripts/  ./scripts/
COPY config/   ./config/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash anatomai
USER anatomai

# Expose API and dashboard ports
EXPOSE 8000 8501

# Default: start FastAPI inference server
# Use sh -c so $PORT (injected by Railway) is shell-expanded at runtime.
# Falls back to 8000 for local Docker runs where PORT is not set.
CMD ["sh", "-c", "uvicorn src.serving.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
