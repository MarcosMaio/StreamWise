FROM python:3.11-slim

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip && pip install \
    "pandas>=2.2.0" \
    "pyarrow>=15.0.0" \
    "pyyaml>=6.0.0" \
    "numpy>=1.26.0" \
    "sqlalchemy[asyncio]>=2.0.36" \
    "asyncpg>=0.30.0" \
    "pydantic-settings>=2.6.0" \
    "pgvector>=0.3.6"

CMD ["python", "ml/eval/evaluate.py"]
