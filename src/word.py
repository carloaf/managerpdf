"""Conversão de PDF em Word (DOCX) via serviço Marker (container separado).

O serviço ``convert`` (Marker em modo CPU ``fast`` + pandoc) recebe o PDF e
devolve o DOCX pronto. Este módulo é o cliente HTTP:

* valida e descriptografa o PDF localmente — o serviço nunca vê senhas;
* envia os bytes para o serviço local (mesma rede Docker, o arquivo não sai
  da máquina);
* devolve o DOCX.

Requer o container ``convert`` em execução (`docker compose up --build`).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .pdf_utils import PDFProcessingError, open_pdf

WORD_SERVICE_URL = os.environ.get("CONVERT_SERVICE_URL", "http://convert:8000").rstrip("/")

# Conversão com IA em CPU pode demorar em PDFs longos; timeout folgado.
_REQUEST_TIMEOUT = 900

# Proteção de memória: o serviço mantém o documento inteiro em RAM.
MAX_PAGES = 200


@dataclass
class WordReport:
    elapsed_s: float


def is_word_available() -> bool:
    """Verifica se o serviço de conversão responde (usado pela interface)."""
    try:
        with urllib.request.urlopen(
            f"{WORD_SERVICE_URL}/health", timeout=5
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def pdf_to_docx(
    data: bytes, password: str | None = None
) -> tuple[bytes, WordReport]:
    """Converte o PDF em DOCX usando o serviço Marker.

    Devolve ``(docx_bytes, WordReport)``. Levanta :class:`PDFProcessingError`
    com mensagem pronta para a interface em caso de falha.
    """
    started = time.time()

    doc = open_pdf(data, password)
    try:
        if doc.page_count > MAX_PAGES:
            raise PDFProcessingError(
                f"O documento tem {doc.page_count} páginas; o limite para "
                f"conversão em Word é de {MAX_PAGES}. Divida o PDF e converta "
                "as partes separadamente."
            )
        # Reescreve o PDF já descriptografado: o serviço nunca recebe a senha.
        clean = doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()

    out = _request_word(clean)
    return out, WordReport(elapsed_s=time.time() - started)


def _request_word(data: bytes) -> bytes:
    request = urllib.request.Request(
        f"{WORD_SERVICE_URL}/word",
        data=data,
        method="POST",
        headers={"Content-Type": "application/pdf"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        message = f"O serviço de conversão retornou um erro ({exc.code})."
        detail = _read_error_detail(exc)
        if detail:
            message = f"{message} {detail}"
        raise PDFProcessingError(message) from exc
    except urllib.error.URLError as exc:
        raise PDFProcessingError(
            "Não foi possível falar com o serviço de conversão. Verifique se "
            "o container 'convert' está em execução (`docker compose up`)."
        ) from exc


def _read_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        # O FastAPI devolve {"detail": "..."}.
        return json.loads(exc.read().decode("utf-8", "replace")).get("detail", "")
    except Exception:  # noqa: BLE001 - corpo não-JSON
        return ""
