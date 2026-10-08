# LeaseLens API as one container: FastAPI + the offline risk model + Tesseract OCR.
# Sized for a 512 MB free tier (Render): embeddings run on ONNX Runtime, not PyTorch.
# Secrets (DATABASE_URL, LLM_API_KEY) are never baked in: set them in the host's dashboard.
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    EMBEDDINGS_BACKEND=onnx
WORKDIR /home/user/app

COPY --chown=user backend/requirements-deploy.txt backend/requirements-deploy.txt
RUN pip install --no-cache-dir --user -r backend/requirements-deploy.txt

# Bake the embedding model into the image, so a restart never waits on a download.
RUN python -c "from huggingface_hub import hf_hub_download as d; m='sentence-transformers/all-MiniLM-L6-v2'; d(m, 'tokenizer.json'); d(m, 'onnx/model.onnx')"
ENV HF_HUB_OFFLINE=1

COPY --chown=user backend/app backend/app
COPY --chown=user data/statute_kb/leaselens_statute_kb.json data/statute_kb/leaselens_statute_index.json data/statute_kb/
COPY --chown=user data/phase4_demo_safe_sample.json data/phase4_raw_results.json data/

ENV ENVIRONMENT=production \
    DEMO_MODE=true \
    RETENTION_HOURS=24 \
    UPLOAD_LIMIT_PER_HOUR=10 \
    ANALYSIS_LIMIT_PER_HOUR=15 \
    CHAT_LIMIT_PER_HOUR=40 \
    CORS_ORIGINS=https://leaselens-india.vercel.app \
    LLM_BASE_URL=https://api.groq.com/openai/v1 \
    LLM_MODEL=qwen/qwen3.8-27b \
    LLM_MIN_INTERVAL_SECONDS=2.5

WORKDIR /home/user/app/backend
EXPOSE 10000
# The host sets PORT (Render: 10000); proxy headers give the rate limiter real client IPs.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips '*'"]
