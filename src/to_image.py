"""Conversão de páginas de PDF em imagens JPG ou PNG.

As páginas são renderizadas com ``Page.get_pixmap(dpi=...)`` e codificadas
diretamente em memória. O gerador :func:`iter_page_images` escreve uma imagem
por vez no ZIP, evitando manter o documento inteiro renderizado em memória.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterator, Sequence

import fitz
from PIL import Image

from .pdf_utils import MAX_OUTPUT_FILES, PDFProcessingError, open_pdf

SUPPORTED_FORMATS = ("png", "jpg")

MIN_DPI = 40
MAX_DPI = 600


@dataclass(frozen=True)
class PageImage:
    """Uma página convertida em imagem."""

    filename: str
    data: bytes


def iter_page_images(
    data: bytes,
    *,
    fmt: str = "png",
    dpi: int = 150,
    quality: int = 90,
    pages: Sequence[int] | None = None,
    stem: str = "documento",
    password: str | None = None,
) -> Iterator[PageImage]:
    """Renderiza as páginas do PDF em imagens, uma de cada vez.

    ``pages`` são índices 0-based; ``None`` converte o documento inteiro.
    ``quality`` só tem efeito para JPG.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        raise PDFProcessingError("Formato inválido. Escolha PNG ou JPG.")
    if not MIN_DPI <= dpi <= MAX_DPI:
        raise PDFProcessingError(
            f"A resolução deve estar entre {MIN_DPI} e {MAX_DPI} DPI."
        )
    if fmt == "jpg" and not 1 <= quality <= 100:
        raise PDFProcessingError("A qualidade JPG deve estar entre 1 e 100.")

    doc = open_pdf(data, password)
    try:
        selected = list(range(doc.page_count)) if pages is None else list(pages)
        if not selected:
            raise PDFProcessingError("Nenhuma página foi selecionada.")
        if len(selected) > MAX_OUTPUT_FILES:
            raise PDFProcessingError(
                f"O limite é de {MAX_OUTPUT_FILES} imagens por operação. "
                "Selecione menos páginas ou divida o PDF antes de converter."
            )

        invalid = [p + 1 for p in selected if p < 0 or p >= doc.page_count]
        if invalid:
            raise PDFProcessingError(
                "Página(s) inexistente(s): "
                + ", ".join(str(p) for p in invalid)
                + f". O documento tem {doc.page_count} páginas."
            )

        digits = max(3, len(str(doc.page_count)))
        for index in selected:
            filename = f"{stem}_pagina_{index + 1:0{digits}d}.{fmt}"
            try:
                pixmap = doc[index].get_pixmap(dpi=dpi)
                yield PageImage(filename, _encode(pixmap, fmt=fmt, quality=quality))
            except PDFProcessingError:
                raise
            except Exception as exc:  # noqa: BLE001 - falha isolada de uma página
                raise PDFProcessingError(
                    f"Não foi possível converter a página {index + 1} em imagem."
                ) from exc
    finally:
        doc.close()


def pdf_to_images(
    data: bytes,
    *,
    fmt: str = "png",
    dpi: int = 150,
    quality: int = 90,
    pages: Sequence[int] | None = None,
    stem: str = "documento",
    password: str | None = None,
) -> list[PageImage]:
    """Versão em lista de :func:`iter_page_images`, útil para testes."""
    return list(
        iter_page_images(
            data,
            fmt=fmt,
            dpi=dpi,
            quality=quality,
            pages=pages,
            stem=stem,
            password=password,
        )
    )


def _encode(pixmap: fitz.Pixmap, *, fmt: str, quality: int) -> bytes:
    """Codifica o pixmap no formato escolhido."""
    if fmt == "png":
        return pixmap.tobytes("png")

    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )
        return buffer.getvalue()
