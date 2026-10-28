"""Pré-visualização de páginas em PNG (usada antes de aplicar transformações)."""

from __future__ import annotations

from .pdf_utils import PDFProcessingError, open_pdf


def render_page_png(
    data: bytes,
    page_index: int = 0,
    *,
    dpi: int = 80,
    rotation: int = 0,
    password: str | None = None,
) -> bytes:
    """Renderiza uma página do PDF em PNG, opcionalmente já rotacionada.

    A rotação é aplicada apenas na cópia em memória — o PDF original do
    usuário não é alterado.
    """
    doc = open_pdf(data, password)
    try:
        if not 0 <= page_index < doc.page_count:
            raise PDFProcessingError(
                f"A página {page_index + 1} não existe neste documento."
            )

        page = doc[page_index]
        if rotation:
            page.set_rotation((page.rotation + rotation) % 360)

        return page.get_pixmap(dpi=dpi).tobytes("png")
    finally:
        doc.close()
