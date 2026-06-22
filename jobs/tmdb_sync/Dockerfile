FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml apps/api/README.md /app/
COPY apps/api/app /app/app

RUN pip install --upgrade pip && pip install ".[ml]"

WORKDIR /jobs/tmdb_sync
COPY jobs/tmdb_sync /jobs/tmdb_sync
COPY jobs/email /jobs/email
COPY ml/training /ml/training
COPY ml/mlflow /ml/mlflow
COPY ml/eval /ml/eval

RUN pip install --upgrade pip && pip install /ml/training

CMD ["python", "scheduler.py"]
