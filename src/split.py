"""Dividir (split) PDFs em intervalos, páginas individuais ou blocos fixos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import fitz

from .pdf_utils import (
    MAX_OUTPUT_FILES,
    PDFProcessingError,
    document_to_bytes,
    open_pdf,
)


@dataclass(frozen=True)
class PDFPart:
    """Um PDF resultante da divisão."""

    filename: str
    data: bytes
    page_count: int


def extract_ranges(
    data: bytes,
    ranges: Sequence[tuple[int, int]],
    *,
    stem: str = "documento",
    password: str | None = None,
    combine: bool = False,
) -> list[PDFPart]:
    """Extrai intervalos 1-based para novos PDFs.

    ``combine=True`` gera um único arquivo com todos os intervalos na ordem
    informada; caso contrário cada intervalo vira um arquivo separado.
    """
    if not ranges:
        raise PDFProcessingError("Nenhum intervalo de páginas foi informado.")
    if len(ranges) > MAX_OUTPUT_FILES:
        raise PDFProcessingError(
            f"O limite é de {MAX_OUTPUT_FILES} arquivos por operação. "
            "Divida o trabalho em partes menores."
        )

    doc = open_pdf(data, password)
    try:
        for start, end in ranges:
            if start < 1 or end < start or end > doc.page_count:
                raise PDFProcessingError(
                    f"Intervalo {start}-{end} fora dos limites do documento "
                    f"({doc.page_count} páginas)."
                )

        if combine:
            data_out, pages = _build_bytes(doc, ranges)
            return [
                PDFPart(
                    filename=f"{stem}_extraido.pdf",
                    data=data_out,
                    page_count=pages,
                )
            ]

        parts: list[PDFPart] = []
        for start, end in ranges:
            data_out, pages = _build_bytes(doc, [(start, end)])
            suffix = f"{start:02d}" if start == end else f"{start:02d}-{end:02d}"
            parts.append(
                PDFPart(
                    filename=f"{stem}_paginas_{suffix}.pdf",
                    data=data_out,
                    page_count=pages,
                )
            )
        return parts
    finally:
        doc.close()


def split_every_page(
    data: bytes,
    *,
    stem: str = "documento",
    password: str | None = None,
) -> list[PDFPart]:
    """Gera um PDF por página do documento."""
    doc = open_pdf(data, password)
    try:
        if doc.page_count > MAX_OUTPUT_FILES:
            raise PDFProcessingError(
                f"O documento tem {doc.page_count} páginas e o limite é de "
                f"{MAX_OUTPUT_FILES} arquivos por operação."
            )
        parts: list[PDFPart] = []
        for index in range(doc.page_count):
            data_out, pages = _build_bytes(doc, [(index + 1, index + 1)])
            parts.append(
                PDFPart(
                    filename=f"{stem}_pagina_{index + 1:03d}.pdf",
                    data=data_out,
                    page_count=pages,
                )
            )
        return parts
    finally:
        doc.close()


def split_in_chunks(
    data: bytes,
    chunk_size: int,
    *,
    stem: str = "documento",
    password: str | None = None,
) -> list[PDFPart]:
    """Divide em blocos consecutivos de ``chunk_size`` páginas."""
    if chunk_size < 1:
        raise PDFProcessingError("O tamanho do bloco deve ser de ao menos 1 página.")

    doc = open_pdf(data, password)
    try:
        total = doc.page_count
        expected = -(-total // chunk_size)  # ceil
        if expected > MAX_OUTPUT_FILES:
            raise PDFProcessingError(
                f"A divisão geraria {expected} arquivos; o limite é "
                f"{MAX_OUTPUT_FILES}. Aumente o tamanho do bloco."
            )

        parts: list[PDFPart] = []
        for start in range(1, total + 1, chunk_size):
            end = min(start + chunk_size - 1, total)
            data_out, pages = _build_bytes(doc, [(start, end)])
            parts.append(
                PDFPart(
                    filename=f"{stem}_paginas_{start:03d}-{end:03d}.pdf",
                    data=data_out,
                    page_count=pages,
                )
            )
        return parts
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------
def _build_bytes(
    source: fitz.Document,
    ranges: Sequence[tuple[int, int]],
) -> tuple[bytes, int]:
    """Monta um PDF novo com as páginas indicadas e devolve ``(bytes, páginas)``."""
    result = fitz.open()
    try:
        for start, end in ranges:
            result.insert_pdf(source, from_page=start - 1, to_page=end - 1)
        return document_to_bytes(result), result.page_count
    except PDFProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PDFProcessingError(
            "Falha ao extrair as páginas solicitadas."
        ) from exc
    finally:
        result.close()
