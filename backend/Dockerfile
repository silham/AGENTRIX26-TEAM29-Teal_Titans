FROM python:3.11-slim

# tesseract/poppler: OCR fallback for scanned document uploads (see README).
# curl: used by the compose healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# CPU-only torch first: sentence-transformers only needs torch>=1.11.0 as a
# local-embedding fallback, but its default wheel drags in the full CUDA
# toolkit (cublas/cudnn/nccl/nvshmem/triton, several GB). Satisfying the
# constraint here keeps the resolver from ever reaching for that build.
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 -r requirements.txt

COPY . .

RUN mkdir -p /app/storage

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STORAGE_DIR=/app/storage

EXPOSE 8000

RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
