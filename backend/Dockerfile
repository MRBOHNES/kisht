FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_NO_DEV=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
