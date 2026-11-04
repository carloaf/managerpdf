# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# managerpdf-ocr — serviço OCR isolado (Indra OCR em ONNX Runtime).
#
# O modelo (~76 MB) é baixado no BUILD, para que o runtime não dependa de rede
# nem do Hugging Face. O container expõe uma API HTTP em :8000; o container
# principal chama POST /ocr e recebe as linhas reconhecidas com coordenadas.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/appuser \
    INDRA_OCR_MODEL_DIR=/opt/indra-models \
    INDRA_THREADS=2 \
    INDRA_DPI=200

WORKDIR /app

# curl é usado apenas pelo HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependências (aproveita cache de build).
# Os caminhos são relativos ao contexto de build (raiz do repositório).
COPY services/ocr/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Baixa os modelos do Indra (~76 MB) direto para /opt/indra-models no build.
RUN python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    "datalab-to/indra-ocr",
    revision="v1.1.0",
    local_dir="/opt/indra-models",
    allow_patterns=["*.onnx", "meta.json", "lm.npz", "lm_*.npz"],
)
PY

COPY services/ocr/app.py ./

# Executa como usuário sem privilégios.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /opt/indra-models /home/appuser /tmp
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
