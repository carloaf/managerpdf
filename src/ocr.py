"""OCR via serviço Indra (container separado) + PDF pesquisável.

O Indra OCR (serviço ``ocr`` no compose) devolve, por página, as linhas
reconhecidas com suas coordenadas na imagem renderizada. Este módulo:

* envia o PDF ao serviço local (mesma rede Docker, arquivo não sai da máquina);
* sobrepõe com PyMuPDF uma camada de texto invisível nas páginas
  digitalizadas, gerando um PDF pesquisável sem alterar a aparência.

Limitação conhecida (v1): o posicionamento do texto é exato para páginas na
orientação normal (``rotation == 0``). Páginas rotacionadas ou em colunas
verticais ainda recebem o texto pesquisável, mas as coordenadas podem não
coincidir com precisão com a linha visual.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import fitz

from .pdf_utils import PDFProcessingError, open_pdf

OCR_SERVICE_URL = os.environ.get("OCR_SERVICE_URL", "http://ocr:8000").rstrip("/")

# PDFs grandes digitalizados podem levar minutos; timeout folgado de segurança.
_REQUEST_TIMEOUT = 600

# Texto invisível: não há custo visual; mantém o arquivo pesquisável.
_FONT = "helv"
_RENDER_MODE_INVISIBLE = 3


@dataclass
class OCRReport:
    pages_total: int
    pages_ocr: int
    pages_text_layer: int
    elapsed_s: float


def is_ocr_available() -> bool:
    """Verifica se o serviço de OCR responde (usado pela interface)."""
    try:
        with urllib.request.urlopen(
            f"{OCR_SERVICE_URL}/health", timeout=5
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def make_searchable_pdf(
    data: bytes, password: str | None = None
) -> tuple[bytes, OCRReport]:
    """Gera um PDF pesquisável a partir do reconhecimento do Indra OCR.

    Devolve ``(pdf_bytes, OCRReport)``. Levanta :class:`PDFProcessingError`
    com mensagem pronta para a interface em caso de falha.
    """
    started = time.time()
    result = _request_ocr(data, password)
    pages_info = result.get("pages") or []
    if not pages_info:
        raise PDFProcessingError("O serviço de OCR não devolveu nenhuma página.")

    doc = open_pdf(data, password)
    total = doc.page_count
    pages_ocr = 0
    pages_text = 0
    try:
        for info in pages_info:
            index = info.get("index")
            if index is None or not 0 <= index < total:
                continue
            source = info.get("source")
            if source == "ocr":
                pages_ocr += 1
                _overlay_text(doc[index], info)
            elif source in ("text", "hybrid"):
                pages_text += 1
        if pages_ocr == 0:
            raise PDFProcessingError(
                "Nenhuma página precisou de OCR: o documento já possui "
                "camada de texto pesquisável."
            )
        out = doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()

    elapsed = time.time() - started
    return out, OCRReport(total, pages_ocr, pages_text, elapsed)


def _request_ocr(data: bytes, password: str | None) -> dict:
    url = f"{OCR_SERVICE_URL}/ocr"
    if password:
        url += f"?password={urllib.parse.quote(password)}"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/pdf"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8", "replace")).get(
                "detail", ""
            )
        except Exception:  # noqa: BLE001 - corpo não-JSON
            detail = ""
        message = f"O serviço de OCR retornou um erro ({exc.code})."
        if detail:
            message = f"{message} {detail}"
        raise PDFProcessingError(message) from exc
    except urllib.error.URLError as exc:
        raise PDFProcessingError(
            "Não foi possível falar com o serviço de OCR. Verifique se o "
            "container 'ocr' está em execução (`docker compose up`)."
        ) from exc


def _overlay_text(page: fitz.Page, info: dict) -> None:
    """Insere a camada de texto invisível em uma página a partir do JSON do OCR."""
    scale = float(info.get("scale") or (200.0 / 72.0))
    for line in info.get("lines", []):
        box = line.get("box")
        if not box or len(box) != 4:
            continue
        text = (line.get("text") or "").strip()
        if not text:
            continue
        x0, y0, x1, y1 = (float(v) / scale for v in box)
        _insert_invisible(page, text, x0, y0, x1, y1)


def _insert_invisible(
    page: fitz.Page,
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> None:
    """Escreve ``text`` invisível (render_mode=3) na caixa dada, em pontos."""
    height = max(y1 - y0, 1.0)
    fontsize = max(4.0, min(20.0, height * 0.75))
    # Linha de base um pouco acima da borda inferior da caixa.
    point = fitz.Point(x0, y1 - max(fontsize * 0.2, 0.5))
    try:
        page.insert_text(
            point,
            text,
            fontsize=fontsize,
            fontname=_FONT,
            render_mode=_RENDER_MODE_INVISIBLE,
        )
    except Exception:  # noqa: BLE001 - caractere fora da fonte base-14: pula a linha
        pass
