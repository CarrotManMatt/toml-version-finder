FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-group dev --group deploy

COPY LICENSE /app/
COPY ./app /app

FROM python:3.14-slim-trixie

RUN groupadd --system --gid 999 nonroot && useradd --system --gid 999 --uid 999 --create-home nonroot

# renovate: release=trixie depName=curl
ENV CURL_VERSION="8.14.*"

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends curl="${CURL_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

LABEL org.opencontainers.image.source=https://github.com/CarrotManMatt/toml-version-finder
LABEL org.opencontainers.image.licenses=GPL-3.0-or-later

HEALTHCHECK CMD curl -f http://localhost:8000/healthcheck || exit 1
COPY --from=builder --chown=nonroot:nonroot /app /app

ENV LANG=C.UTF-8 PATH="/app/.venv/bin:$PATH"

USER nonroot

ENTRYPOINT [ \
    "gunicorn", \
    "main:app", \
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
