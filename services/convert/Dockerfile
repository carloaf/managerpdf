# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# managerpdf-convert — serviço de conversão PDF → Word (Marker em CPU + pandoc).
#
# Os modelos do Indra (~76 MB) e a fonte de renderização do Marker são baixados
# no BUILD, para que o runtime não dependa de rede. O container expõe uma API
# HTTP em :8000; o container principal chama POST /word e recebe o DOCX.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/appuser \
    XDG_CACHE_HOME=/opt/cache \
    INDRA_OCR_MODEL_DIR=/opt/indra-models \
    INDRA_THREADS=2

WORKDIR /app

# curl (healthcheck + download de artefatos) e pandoc (Markdown → DOCX).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl pandoc \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependências (aproveita cache de build).
# Os caminhos são relativos ao contexto de build (raiz do repositório).
COPY services/convert/requirements.txt ./
# O índice extra fornece as rodas CPU de torch/torchvision (pins no arquivo).
RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# Baixa os modelos do Indra (~76 MB) direto para /opt/indra-models no build
# (mesma base usada pelo serviço de OCR).
RUN python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    "datalab-to/indra-ocr",
    revision="v1.1.0",
    local_dir="/opt/indra-models",
    allow_patterns=["*.onnx", "meta.json", "lm.npz", "lm_*.npz"],
)
PY

# Fonte de renderização do Marker (~15 MB), exigida em runtime pelo renderer.
RUN mkdir -p /opt/cache/datalab/marker/fonts \
    && curl -fsSL --retry 3 -o /opt/cache/datalab/marker/fonts/GoNotoCurrent-Regular.ttf \
       https://models.datalab.to/artifacts/GoNotoCurrent-Regular.ttf

COPY services/convert/app.py ./

# Executa como usuário sem privilégios.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /opt/cache /opt/indra-models /home/appuser /tmp
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
