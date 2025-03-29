# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml .

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=./requirements_fastapi.txt,target=./requirements.txt \
    uv pip install --no-cache-dir -r ./requirements.txt

RUN uv pip install --no-cache-dir -e .

COPY . /app/api

EXPOSE 8000
