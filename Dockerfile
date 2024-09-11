# ---- Development Stage ----

ARG PYTHON_VERSION=3.12

FROM mcr.microsoft.com/devcontainers/python:1-${PYTHON_VERSION} AS development

WORKDIR /app
#VOLUME /app/instance

COPY . .

# Install tools
RUN --mount=type=cache,target=/root/.cache/pip \
    pipx install poetry ruff pre-commit isort && \
    poetry completions bash | sudo tee -a /etc/profile.d/75-poetry.sh

# Setup instance path and make it writable
ENV INSTANCE_PATH=/app/instance
RUN mkdir -p $INSTANCE_PATH && \
    chown vscode:vscode $INSTANCE_PATH

# Set up environment for user
USER vscode

RUN poetry install --no-cache --no-interaction --with dev && \
    echo 'source $(poetry env info --path)/bin/activate' >> ~/.bashrc && \
    poetry run pip install --no-cache-dir -e .

CMD ["uvicorn", "--host=0.0.0.0", "--port=8000", "gardenparty.app:app"]
