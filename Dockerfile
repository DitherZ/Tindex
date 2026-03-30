# ──── TINDEX DOCKER IMAGE ──── #
# Multi-stage build for minimal image size

FROM python:3.13-slim AS base

LABEL maintainer="Blackflame (DitherZ)"
LABEL description="Tindex — Telegram media index & streaming server"

WORKDIR /app

# Install system deps for cryptg (optional C extension)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY tindex/ tindex/

RUN pip install --no-cache-dir ".[fast]"

EXPOSE 8080

CMD ["python", "-m", "tindex"]
