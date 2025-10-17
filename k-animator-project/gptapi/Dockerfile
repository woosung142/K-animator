FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH=/app

WORKDIR /app

COPY gptapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/

COPY gptapi/ /app/gptapi/

EXPOSE 8004

CMD ["uvicorn", "gptapi.main:app", "--host", "0.0.0.0", "--port", "8004"]
#...