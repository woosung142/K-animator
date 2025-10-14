FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH /app

WORKDIR /app

COPY auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/

COPY auth/ /app/auth/

EXPOSE 8001

CMD ["uvicorn", "auth.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]