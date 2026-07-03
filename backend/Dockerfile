FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/tests /app/backend/tests
COPY runner /app/runner

WORKDIR /app/backend

RUN pip install --no-cache-dir -e ".[dev]" && pip install --no-cache-dir -e /app/runner

ENV PYTHONPATH=/app/backend:/app/runner
ENV ARTIFACTS_DIR=/app/artifacts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
