# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend-build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build
# Produces /frontend-build/dist/

# ── Stage 2: Python application ───────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing (ffmpeg for faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models into the image layer so the first request is fast.
# Both downloads are non-fatal (|| true) to keep builds working in air-gapped envs.
ARG WHISPER_MODEL=base
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')" \
    || echo "WARNING: Whisper model download failed — will download at runtime"

ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')" \
    || echo "WARNING: Embedding model download failed — will download at runtime"

COPY . .

# Copy the built frontend into the expected location
COPY --from=frontend-builder /frontend-build/dist ./frontend/dist

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
