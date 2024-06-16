# Use an official Python runtime as the base image
FROM mcr.microsoft.com/devcontainers/python:0-3.11-bullseye

ARG WASMIOT_ORCHESTRATOR_URL
ENV WASMIOT_ORCHESTRATOR_URL=${WASMIOT_ORCHESTRATOR_URL:-http://orchestrator:3000}

ENV PYTHONUNBUFFERED 1

EXPOSE 7860

# Set the working directory in the container
WORKDIR /app

COPY . .

# Install the dependencies
RUN --mount=type=cache,target=/root/.cache/pip pip  --disable-pip-version-check install -e .


# Specify the command to run when the container starts
CMD [ "python", "-m", "icwe-demo" ]
