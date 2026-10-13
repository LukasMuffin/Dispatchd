# One image for both the API and the worker; docker-compose picks the command.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so they're cached separately from source changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

EXPOSE 8000
CMD ["uvicorn", "dispatchd.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
