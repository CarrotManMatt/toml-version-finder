FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-group dev --group deploy

COPY . /app

FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.source=https://github.com/CarrotManMatt/toml-version-finder
LABEL org.opencontainers.image.licenses=GPL-3.0-or-later

COPY --from=builder --chown=app:app /app /app

ENV LANG=C.UTF-8 PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ \
    "gunicorn", \
    "app:app", \
    "--chdir", \
    "/app", \
    "-w", \
    "4", \
    "-k", \
    "uvicorn_worker.UvicornWorker", \
    "--access-logfile", \
    "-", \
    "--bind", \
    ":8000" \
]
