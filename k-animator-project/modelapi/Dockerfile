FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH=/app

WORKDIR /app

COPY modelapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/

COPY modelapi/ /app/modelapi/

EXPOSE 8002

CMD ["uvicorn", "modelapi.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
#...