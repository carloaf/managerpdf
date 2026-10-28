"""Juntar (merge) múltiplos PDFs em um único documento."""

from __future__ import annotations

from typing import Mapping, Sequence

import fitz

from .pdf_utils import PDFProcessingError, document_to_bytes, open_pdf


def merge_pdfs(
    files: Sequence[tuple[str, bytes]],
    passwords: Mapping[str, str] | None = None,
) -> bytes:
    """Combina ``files`` na ordem recebida e devolve os bytes do PDF final.

    Parâmetros
    ----------
    files:
        Sequência de ``(nome_original, bytes_do_pdf)`` na ordem desejada.
    passwords:
        Mapa opcional ``nome_original -> senha`` para arquivos protegidos.
    """
    if len(files) < 2:
        raise PDFProcessingError(
            "Selecione ao menos dois arquivos PDF para juntar."
        )

    passwords = passwords or {}
    merged = fitz.open()
    try:
        for name, data in files:
            source = open_pdf(data, passwords.get(name), filename=name)
            try:
                merged.insert_pdf(source)
            except PDFProcessingError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise PDFProcessingError(
                    f"Não foi possível copiar as páginas de '{name}'."
                ) from exc
            finally:
                source.close()

        if merged.page_count == 0:
            raise PDFProcessingError(
                "O resultado ficou sem páginas. Verifique os arquivos enviados."
            )

        return document_to_bytes(merged, garbage=4, deflate=True)
    finally:
        merged.close()
