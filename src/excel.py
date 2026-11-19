"""Conversão de PDF em planilha (XLSX / ODS) por extração de tabelas.

A detecção usa ``Page.find_tables()`` do PyMuPDF — rápido, sem IA e sem rede —
que reconhece tabelas delimitadas por linhas (``strategy="lines"``) ou por
alinhamento de texto (``strategy="text"``). A gravação usa ``openpyxl`` (XLSX)
e ``odfpy`` (ODS).

PDFs escaneados (sem camada de texto) normalmente não expõem tabelas: a
interface orienta a aplicar a ferramenta de OCR antes e tentar novamente.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterator, Sequence

import fitz

from .pdf_utils import PDFProcessingError, open_pdf

SUPPORTED_FORMATS = ("xlsx", "ods")

# Limite de segurança para não monopolizar memória com muitas tabelas.
MAX_TABLES = 300

# Estratégias aceitas por Page.find_tables().
STRATEGIES = ("lines", "text")


@dataclass(frozen=True)
class ExtractedTable:
    """Uma tabela detectada em uma página."""

    page_number: int  # 1-based
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class SpreadsheetReport:
    tables_found: int
    pages_with_tables: int
    total_rows: int


def pdf_to_spreadsheet(
    data: bytes,
    *,
    fmt: str = "xlsx",
    pages: Sequence[int] | None = None,
    strategy: str = "lines",
    password: str | None = None,
) -> tuple[bytes, SpreadsheetReport]:
    """Converte as tabelas do PDF em um arquivo XLSX ou ODS.

    Devolve ``(arquivo_bytes, SpreadsheetReport)``. ``pages`` são índices
    0-based; ``None`` varre o documento inteiro.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        raise PDFProcessingError("Formato inválido. Escolha XLSX ou ODS.")
    if strategy not in STRATEGIES:
        raise PDFProcessingError("Estratégia inválida de detecção de tabelas.")

    tables = list(
        iter_extracted_tables(
            data,
            pages=pages,
            strategy=strategy,
            password=password,
        )
    )
    if not tables:
        raise PDFProcessingError(
            "Nenhuma tabela foi encontrada neste documento. Se ele foi "
            "digitalizado (escaneado), aplique a ferramenta de OCR antes e "
            "tente novamente."
        )

    out = _build_xlsx(tables) if fmt == "xlsx" else _build_ods(tables)
    total_rows = sum(len(t.rows) for t in tables)
    return out, SpreadsheetReport(
        tables_found=len(tables),
        pages_with_tables=len({t.page_number for t in tables}),
        total_rows=total_rows,
    )


def iter_extracted_tables(
    data: bytes,
    *,
    pages: Sequence[int] | None = None,
    strategy: str = "lines",
    password: str | None = None,
) -> Iterator[ExtractedTable]:
    """Percorre as tabelas detectadas, uma de cada vez (memória constante)."""
    doc = open_pdf(data, password)
    try:
        total = doc.page_count
        selected = list(range(total)) if pages is None else [int(p) for p in pages]
        if not selected:
            raise PDFProcessingError("Nenhuma página foi selecionada.")

        invalid = [p + 1 for p in selected if p < 0 or p >= total]
        if invalid:
            raise PDFProcessingError(
                "Página(s) inexistente(s): "
                + ", ".join(str(p) for p in invalid)
                + f". O documento tem {total} páginas."
            )

        emitted = 0
        for index in selected:
            try:
                tabs = doc[index].find_tables(strategy=strategy)
            except Exception as exc:  # noqa: BLE001 - página incomum
                raise PDFProcessingError(
                    f"Não foi possível analisar a página {index + 1}."
                ) from exc

            for table in tabs.tables:
                if emitted >= MAX_TABLES:
                    raise PDFProcessingError(
                        f"O limite é de {MAX_TABLES} tabelas por operação. "
                        "Selecione menos páginas ou divida o PDF antes."
                    )
                rows = _normalize_table(table.extract())
                if _is_empty(rows):
                    continue
                emitted += 1
                yield ExtractedTable(page_number=index + 1, rows=rows)
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Gravação em XLSX / ODS
# ---------------------------------------------------------------------------
def _build_xlsx(tables: Sequence[ExtractedTable]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Resumo"

    header_fill = PatternFill("solid", fgColor="E11D48")
    header_font = Font(bold=True, color="FFFFFF")

    summary.append(["Tabela", "Página", "Linhas", "Colunas"])
    for cell in summary[1]:
        cell.fill = header_fill
        cell.font = header_font

    for index, table in enumerate(tables, start=1):
        columns = len(table.rows[0]) if table.rows else 0
        summary.append([f"Tabela {index}", table.page_number, len(table.rows), columns])
    _autosize_columns(summary)

    for index, table in enumerate(tables, start=1):
        sheet = workbook.create_sheet(title=f"Tabela {index}")
        for row in table.rows:
            sheet.append(list(row))
        _autosize_columns(sheet)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_ods(tables: Sequence[ExtractedTable]) -> bytes:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    for index, table in enumerate(tables, start=1):
        sheet = Table(name=f"Tabela {index}")
        for row in table.rows:
            table_row = TableRow()
            for value in row:
                cell = TableCell(valuetype="string")
                cell.addElement(P(text=value))
                table_row.addElement(cell)
            sheet.addElement(table_row)
        doc.spreadsheet.addElement(sheet)

    buffer = io.BytesIO()
    doc.write(buffer)
    return buffer.getvalue()


def _autosize_columns(sheet, *, max_width: int = 60) -> None:
    """Ajusta a largura das colunas ao maior conteúdo (limitada a ``max_width``)."""
    from openpyxl.utils import get_column_letter

    for column in sheet.columns:
        values = [str(cell.value) if cell.value is not None else "" for cell in column]
        if not values:
            continue
        longest = max(len(value) for value in values)
        letter = get_column_letter(column[0].column)
        sheet.column_dimensions[letter].width = max(8, min(max_width, longest + 2))


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def _normalize_table(
    raw: Sequence[Sequence[str | None]],
) -> tuple[tuple[str, ...], ...]:
    """Converte a saída do PyMuPDF em linhas limpas, removendo linhas vazias."""
    rows: list[tuple[str, ...]] = []
    for raw_row in raw:
        row = tuple(
            " ".join(str(cell).split()) if cell is not None else ""
            for cell in raw_row
        )
        if any(cell for cell in row):
            rows.append(row)
    return tuple(rows)


def _is_empty(rows: tuple[tuple[str, ...], ...]) -> bool:
    return not rows or not any(cell for row in rows for cell in row)
