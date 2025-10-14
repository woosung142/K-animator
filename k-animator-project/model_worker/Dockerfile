FROM python:3.10-slim AS base
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential imagemagick libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

FROM base AS builder
WORKDIR /app
COPY model-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS final
WORKDIR /app
ENV PYTHONPATH /app

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY shared/ /app/shared/
COPY model_worker/ /app/model_worker/

CMD ["celery", "-A", "model-worker.worker:celery_app", "worker", "--loglevel=info"]