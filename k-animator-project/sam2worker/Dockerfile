FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-devel

WORKDIR /app

# To handle Korean filenames
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Models and data will be mounted as volumes in docker-compose
# SAM2_MODEL_PATH: /media/kanimator-sd-models/sam2-model
# SHARED_DATA_PATH: /app/data (or similar)

CMD ["celery", "-A", "worker.app", "worker", "--loglevel=info", "-Q", "sam2_queue"]