FROM python:3.10-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

FROM base

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY utils/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/

COPY utils/ /app/utils/

EXPOSE 8003

CMD ["uvicorn", "util.web:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
#.