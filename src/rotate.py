"""Rotação de páginas de um PDF."""

from __future__ import annotations

from typing import Sequence

from .pdf_utils import PDFProcessingError, document_to_bytes, open_pdf

VALID_ANGLES = (90, 180, 270)


def rotate_pdf(
    data: bytes,
    angle: int,
    pages: Sequence[int] | None = None,
    *,
    password: str | None = None,
) -> bytes:
    """Rotaciona o PDF em ``angle`` graus (90/180/270).

    ``pages`` são índices 0-based; se ``None``, todas as páginas são
    rotacionadas. A rotação é somada à rotação já existente de cada página.
    """
    if angle not in VALID_ANGLES:
        raise PDFProcessingError(
            "Ângulo inválido. Escolha 90, 180 ou 270 graus."
        )

    doc = open_pdf(data, password)
    try:
        if pages is None:
            targets = range(doc.page_count)
        else:
            targets = sorted(set(pages))
            if not targets:
                raise PDFProcessingError("Nenhuma página foi selecionada.")
            invalid = [p + 1 for p in targets if p < 0 or p >= doc.page_count]
            if invalid:
                raise PDFProcessingError(
                    "Página(s) inexistente(s): "
                    + ", ".join(str(p) for p in invalid)
                    + f". O documento tem {doc.page_count} páginas."
                )

        for index in targets:
            page = doc[index]
            page.set_rotation((page.rotation + angle) % 360)

        return document_to_bytes(doc, garbage=3, deflate=True)
    finally:
        doc.close()
