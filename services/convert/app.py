"""Serviço de conversão do managerpdf: Marker (CPU) + pandoc → DOCX.

Recebe o PDF como corpo bruto (Content-Type: application/pdf) e devolve o
DOCX correspondente. O pipeline:

    PDF → Marker (modo ``fast``, Indra ONNX em CPU) → HTML
        → pandoc → DOCX

Usamos o HTML do Marker (e não o Markdown) porque ele preserva tabelas e
fórmulas como elementos nativos, que o pandoc converte em tabelas e equações
reais do Word.

Os modelos do Indra vêm do diretório local ``INDRA_OCR_MODEL_DIR`` (baixados
no build da imagem), então o runtime não precisa de rede. O mesmo vale para a
fonte de renderização do Marker (pré-baixada em ``XDG_CACHE_HOME``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

THREADS = int(os.environ.get("INDRA_THREADS", "2"))

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

_converter = None
_lock = threading.Lock()


def get_converter():
    """Devolve o PdfConverter do Marker carregado uma única vez (em RAM)."""
    global _converter
    with _lock:
        if _converter is None:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.ocr import IndraRecognitionPredictor

            # create_model_dict() instancia o preditor com 4 threads fixas; aqui
            # recriamos com INDRA_THREADS para respeitar o limite da VM.
            artifacts = create_model_dict(load_indra=False)
            indra = IndraRecognitionPredictor(threads=THREADS)
            artifacts.update(
                {
                    "layout_model": indra,
                    "fast_layout_model": indra,
                    "indra_model": indra,
                }
            )

            _converter = PdfConverter(
                artifact_dict=artifacts,
                renderer="marker.renderers.html.HTMLRenderer",
                config={"mode": "fast"},
            )
        return _converter


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Carrega os modelos na subida: falha cedo se a imagem não tiver os modelos.
    get_converter()
    yield


app = FastAPI(title="managerpdf-convert", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine": "marker", "mode": "fast", "threads": THREADS}


@app.post("/word")
async def word(request: Request) -> Response:
    """Recebe um PDF (corpo da requisição) e devolve o DOCX correspondente."""
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="arquivo vazio")

    try:
        docx = await run_in_threadpool(_convert_to_docx, data)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - devolve detalhe no HTTP 500
        raise HTTPException(status_code=500, detail=f"falha na conversão: {exc}") from exc

    return Response(content=docx, media_type=DOCX_MIME)


def _convert_to_docx(data: bytes) -> bytes:
    converter = get_converter()
    with tempfile.TemporaryDirectory(prefix="managerpdf-convert-") as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / "input.pdf"
        pdf_path.write_bytes(data)

        rendered = converter(str(pdf_path))

        from marker.output import text_from_rendered

        html_text, _ext, images = text_from_rendered(rendered)
        if not html_text or not html_text.strip():
            raise RuntimeError("o Marker não produziu conteúdo para este PDF")

        _save_images(images, tmp_path)
        html_path = tmp_path / "input.html"
        html_path.write_text(html_text, encoding="utf-8")

        docx_path = tmp_path / "output.docx"
        _run_pandoc(html_path, docx_path, tmp_path)
        return docx_path.read_bytes()


def _save_images(images: dict, tmp_path: Path) -> None:
    """Grava as imagens extraídas para o pandoc embuti-las no DOCX."""
    for name, image in images.items():
        try:
            dest = tmp_path / Path(name).name
            fmt = "PNG" if dest.suffix.lower() == ".png" else "JPEG"
            if fmt == "JPEG" and getattr(image, "mode", "RGB") != "RGB":
                image = image.convert("RGB")
            image.save(dest, fmt)
        except Exception:  # noqa: BLE001 - imagem que falha não deve abortar a conversão
            continue


def _run_pandoc(html_path: Path, docx_path: Path, tmp_path: Path) -> None:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("pandoc não está instalado no container 'convert'")

    result = subprocess.run(
        [
            pandoc,
            "-f",
            "html",
            "-t",
            "docx",
            str(html_path),
            "-o",
            str(docx_path),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc falhou: {result.stderr.strip()[:500]}")
