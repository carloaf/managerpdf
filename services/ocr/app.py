"""Serviço OCR do managerpdf: expõe o Indra OCR via HTTP.

Recebe o PDF como corpo bruto (Content-Type: application/pdf) e devolve, para
cada página, as linhas reconhecidas com suas coordenadas (pixels da imagem
renderizada), para que o container principal reconstrua um PDF pesquisável.

Os modelos vêm do diretório local ``INDRA_OCR_MODEL_DIR`` (baixados no build
da imagem), então o runtime não precisa de rede.
"""

from __future__ import annotations

import math
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import pypdfium2 as pdfium
from fastapi import FastAPI, HTTPException, Query, Request

import indra_ocr

MAX_PAGE_PIXELS = 100e6  # mesmo limite interno do Indra (document.py)
DPI = float(os.environ.get("INDRA_DPI", "200"))
THREADS = int(os.environ.get("INDRA_THREADS", "2"))

converter: indra_ocr.Converter | None = None


def get_converter() -> indra_ocr.Converter:
    """Devolve o Converter carregado uma única vez (os modelos ficam em RAM)."""
    global converter
    if converter is None:
        converter = indra_ocr.load(threads=THREADS, dpi=DPI, mode="auto")
    return converter


def _page_scale(width_pt: float, height_pt: float) -> float:
    """Pixels por ponto para uma página (réplica do cálculo interno do Indra)."""
    k = DPI / 72.0
    return min(k, math.sqrt(MAX_PAGE_PIXELS / max(width_pt * height_pt, 1.0)))


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Carrega os modelos na subida: falha cedo se a imagem não tiver os modelos.
    get_converter()
    yield


app = FastAPI(title="managerpdf-ocr", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "threads": THREADS, "dpi": DPI}


@app.post("/ocr")
async def ocr(
    request: Request,
    password: str | None = Query(default=None),
) -> dict:
    """Recebe um PDF (corpo da requisição) e devolve o OCR de todas as páginas.

    Resposta: ``{"dpi": 200.0, "pages": [{index, source, rotation, vertical,
    width_pt, height_pt, scale, lines: [{box, text, conf}]}]}``.
    """
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="arquivo vazio")

    converter = get_converter()

    with tempfile.TemporaryDirectory(prefix="managerpdf-ocr-") as tmp:
        pdf_path = Path(tmp) / "input.pdf"
        pdf_path.write_bytes(data)

        try:
            doc = pdfium.PdfDocument(str(pdf_path), password=password)
        except pdfium.PdfiumError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"não foi possível abrir o PDF: {exc}",
            ) from exc

        pages_out: list[dict] = []
        try:
            sizes = [doc[i].get_size() for i in range(len(doc))]
            for index, page in converter.convert(
                str(pdf_path), password=password
            ):
                width_pt, height_pt = sizes[index]
                pages_out.append(
                    {
                        "index": index,
                        "source": page.source,
                        "rotation": page.rotation,
                        "vertical": page.vertical,
                        "skew": page.skew,
                        "width_pt": round(width_pt, 2),
                        "height_pt": round(height_pt, 2),
                        "scale": round(_page_scale(width_pt, height_pt), 6),
                        "note": page.note,
                        "lines": [
                            {
                                "box": [round(v, 1) for v in line.box],
                                "text": line.text,
                                "conf": round(float(line.conf), 4),
                            }
                            for line in page.lines
                        ],
                    }
                )
        finally:
            doc.close()

    return {"dpi": DPI, "pages": pages_out}
