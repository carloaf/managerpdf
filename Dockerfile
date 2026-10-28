# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# managerpdf — imagem única com todas as dependências instaladas no container.
# Nada precisa ser instalado no host além do Docker.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Boas práticas de execução em container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/appuser \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    TMPDIR=/tmp

WORKDIR /app

# curl é usado apenas pelo HEALTHCHECK
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependências (aproveita cache de build)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY app.py ./
COPY src ./src
COPY ui ./ui
COPY .streamlit ./.streamlit

# Executa como usuário sem privilégios
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /home/appuser /tmp
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
