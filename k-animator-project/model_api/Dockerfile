FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH=/app

WORKDIR /app

COPY model_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/

COPY model_api/ /app/model_api/

EXPOSE 8002

CMD ["uvicorn", "model-api.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
#..