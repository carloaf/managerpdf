"""Utilidades compartilhadas: validação, leitura segura, paginação e formatação."""

from __future__ import annotations

import re
from typing import Iterable, Sequence

import fitz  # PyMuPDF

# Limite de segurança para operações que geram muitos arquivos (split, imagens).
MAX_OUTPUT_FILES = 300

# "1-3", "5", " 8 - 10 "
_RANGE_RE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+)\s*)?$")


class PDFProcessingError(Exception):
    """Erro amigável: a mensagem é exibida diretamente para o usuário."""


class PDFPasswordError(PDFProcessingError):
    """O PDF está protegido por senha (ou a senha informada é inválida)."""


# ---------------------------------------------------------------------------
# Abertura / validação
# ---------------------------------------------------------------------------
def open_pdf(
    data: bytes,
    password: str | None = None,
    filename: str = "documento.pdf",
) -> fitz.Document:
    """Abre um PDF em memória validando o conteúdo e a senha.

    O documento devolvido é de responsabilidade de quem chamou (usar
    ``try/finally`` ou ``with``). Em caso de falha, levanta
    :class:`PDFProcessingError` ou :class:`PDFPasswordError` com mensagem
    pronta para exibição.
    """
    if not data:
        raise PDFProcessingError(f"O arquivo '{filename}' está vazio.")

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - qualquer falha do MuPDF
        raise PDFProcessingError(
            f"'{filename}' não é um PDF válido ou está corrompido."
        ) from exc

    if doc.needs_pass:
        if not password:
            doc.close()
            raise PDFPasswordError(f"'{filename}' está protegido por senha.")
        if not doc.authenticate(password):
            doc.close()
            raise PDFPasswordError(f"Senha incorreta para '{filename}'.")

    if doc.page_count == 0:
        doc.close()
        raise PDFProcessingError(f"'{filename}' não possui páginas legíveis.")

    return doc


def page_count_of(
    data: bytes,
    password: str | None = None,
    filename: str = "documento.pdf",
) -> int:
    """Quantidade de páginas do PDF (abrindo e fechando o documento)."""
    doc = open_pdf(data, password, filename)
    try:
        return doc.page_count
    finally:
        doc.close()


def document_to_bytes(
    doc: fitz.Document,
    *,
    garbage: int = 3,
    deflate: bool = True,
    clean: bool = False,
) -> bytes:
    """Serializa um ``fitz.Document`` para bytes com compactação básica."""
    try:
        return doc.tobytes(garbage=garbage, deflate=deflate, clean=clean)
    except Exception as exc:  # noqa: BLE001
        raise PDFProcessingError(
            "Não foi possível gerar o PDF de saída. O arquivo pode estar danificado."
        ) from exc


# ---------------------------------------------------------------------------
# Leitura de intervalos de páginas
# ---------------------------------------------------------------------------
def parse_page_ranges(spec: str, page_count: int) -> list[tuple[int, int]]:
    """Converte ``"1-3, 5, 8-10"`` em ``[(1, 3), (5, 5), (8, 10)]`` (1-based).

    Valida contra ``page_count`` e levanta :class:`PDFProcessingError` com
    mensagem clara quando o texto é inválido ou fora dos limites.
    """
    if not spec or not spec.strip():
        raise PDFProcessingError(
            "Informe ao menos um intervalo de páginas (ex.: 1-3, 5)."
        )

    ranges: list[tuple[int, int]] = []
    for chunk in spec.split(","):
        if not chunk.strip():
            continue

        match = _RANGE_RE.match(chunk)
        if not match:
            raise PDFProcessingError(
                f"Intervalo inválido: '{chunk.strip()}'. Use o formato 1-3, 5, 8-10."
            )

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start

        if start < 1:
            raise PDFProcessingError("As páginas começam em 1.")
        if end < start:
            raise PDFProcessingError(
                f"Intervalo inválido: '{chunk.strip()}'. O fim deve ser maior ou igual ao início."
            )
        if end > page_count:
            raise PDFProcessingError(
                f"O intervalo {start}-{end} excede o total de {page_count} página(s) do documento."
            )
        ranges.append((start, end))

    if not ranges:
        raise PDFProcessingError(
            "Nenhum intervalo válido foi informado (ex.: 1-3, 5)."
        )

    return ranges


def parse_page_selection(spec: str, page_count: int) -> list[int]:
    """Converte ``"1, 3, 5-7"`` em índices 0-based ordenados e sem repetição."""
    ranges = parse_page_ranges(spec, page_count)
    pages: set[int] = set()
    for start, end in ranges:
        pages.update(range(start - 1, end))
    return sorted(pages)


def ranges_to_pages(ranges: Sequence[tuple[int, int]]) -> list[int]:
    """Expande ``[(1, 3), (7, 7)]`` em índices 0-based."""
    pages: list[int] = []
    for start, end in ranges:
        pages.extend(range(start - 1, end))
    return pages


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------
def human_size(num_bytes: int | float) -> str:
    """Formata bytes em algo legível (ex.: ``1.4 MB``)."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def safe_stem(filename: str) -> str:
    """Extrai o nome base do arquivo removendo extensão e caracteres estranhos."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    stem = re.sub(r"[^\w\-. ]+", "_", stem, flags=re.UNICODE).strip(" ._-")
    return stem or "documento"


def total_pages(ranges: Iterable[tuple[int, int]]) -> int:
    """Soma a quantidade de páginas cobertas pelos intervalos."""
    return sum(end - start + 1 for start, end in ranges)
