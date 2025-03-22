# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

ENV UV_COMPILE_BYTECODE=1
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=./requirements_fastapi.txt,target=./requirements.txt \
    uv pip install -r ./requirements.txt

COPY . /app

EXPOSE 8000
#ENTRYPOINT ["uvicorn", "app:app", "--host" , "0.0.0.0", "--port", "8000"]
