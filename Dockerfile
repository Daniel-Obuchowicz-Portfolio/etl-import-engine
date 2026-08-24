FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app app
COPY pyproject.toml README.md ./
COPY app ./app
COPY mock_api ./mock_api
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./
RUN pip install --upgrade pip && pip install .

USER app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

