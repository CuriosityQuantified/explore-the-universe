FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libvips42 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY api ./api
COPY pipeline ./pipeline
COPY shared ./shared

RUN pip install --no-cache-dir .

CMD ["/bin/sh", "-c", "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]