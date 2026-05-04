# ==============================================================================
# E'assistant — Dockerfile
# ==============================================================================

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Обновляем yt-dlp до последней версии (важно для актуальных форматов YouTube)
RUN pip install --no-cache-dir --upgrade "yt-dlp>=2025.1.1"

# Copy source
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
