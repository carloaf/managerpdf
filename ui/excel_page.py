"""Ferramenta: converter tabelas de um PDF para Excel (XLSX) ou Calc (ODS)."""

from __future__ import annotations

import streamlit as st

from src.excel import pdf_to_spreadsheet
from src.pdf_utils import PDFProcessingError, human_size, parse_page_selection, safe_stem
from src.preview import render_page_png
from ui import components, theme

_RESULT_KEY = "excel_result"

_MIMES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
}

_FORMATS = {
    "Excel (.xlsx)": "xlsx",
    "Calc (.ods)": "ods",
}

_STRATEGIES = {
    "Linhas/bordas (padrão)": "lines",
    "Texto alinhado (sem bordas)": "text",
}

_ALL_PAGES = "Todas as páginas"
_SELECTED_PAGES = "Páginas selecionadas"


def render() -> None:
    theme.hero(
        "📊",
        "PDF para Excel",
        "Extraia as tabelas do PDF e receba uma planilha XLSX ou ODS, com "
        "uma aba por tabela e um resumo indicando a página de origem.",
    )

    uploads = components.upload_pdfs("Selecione o arquivo PDF", key="excel_upload")
    if not uploads:
        st.info("Envie um PDF que contenha tabelas para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="excel_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input(
        "excel_signature", (name, len(data)), _RESULT_KEY
    )
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    fmt, scope, spec, strategy = _render_options(total)
    _render_preview(data, password)

    if st.button("📊 Extrair tabelas", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        _run(data, password, name, total, fmt, scope, spec, strategy)

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar planilha",
        caption="Cada tabela vira uma aba; a primeira aba resume a origem de cada uma.",
    )
    theme.footer()


def _render_options(total: int) -> tuple[str, str, str, str]:
    with st.container(border=True):
        st.markdown("**Opções de extração**")
        col_format, col_strategy = st.columns(2)
        fmt_label = col_format.selectbox(
            "Formato de saída",
            options=list(_FORMATS),
            index=0,
            key="excel_format",
        )
        strategy_label = col_strategy.selectbox(
            "Detecção de tabelas",
            options=list(_STRATEGIES),
            index=0,
            key="excel_strategy",
            help="Use 'Texto alinhado' para tabelas sem linhas de borda visíveis.",
        )

        scope = st.radio(
            "Páginas",
            options=(_ALL_PAGES, _SELECTED_PAGES),
            horizontal=True,
            key="excel_scope",
        )

        spec = ""
        if scope == _SELECTED_PAGES:
            spec = st.text_input(
                "Intervalos de páginas",
                value=f"1-{total}" if total else "",
                placeholder="Ex.: 1, 3, 5-7",
                key="excel_pages",
                help="Aceita páginas isoladas e intervalos, separados por vírgula.",
            )

    st.caption(
        "A detecção usa o PyMuPDF (sem IA, instantânea). PDFs escaneados sem "
        "camada de texto precisam passar pela ferramenta de OCR antes."
    )

    return fmt_label, scope, spec, strategy_label


def _render_preview(data: bytes, password: str | None) -> None:
    """Miniatura da primeira página para conferir o documento enviado."""
    try:
        preview = render_page_png(data, 0, dpi=70, password=password)
    except Exception:  # noqa: BLE001 - prévia é opcional
        return
    st.image(preview, caption="Prévia da página 1", width=320)


def _run(
    data: bytes,
    password: str | None,
    name: str,
    total: int,
    fmt_label: str,
    scope: str,
    spec: str,
    strategy_label: str,
) -> None:
    pages: list[int] | None = None
    if scope == _SELECTED_PAGES:
        try:
            pages = parse_page_selection(spec, total)
        except PDFProcessingError as exc:
            st.error(f"⚠️ {exc}")
            return

    fmt = _FORMATS[fmt_label]
    strategy = _STRATEGIES[strategy_label]
    stem = safe_stem(name)

    with st.spinner("Localizando e extraindo as tabelas..."):
        result = components.run_safely(
            pdf_to_spreadsheet,
            data,
            fmt=fmt,
            pages=pages,
            strategy=strategy,
            password=password,
        )

    if result is None:
        return

    sheet_bytes, report = result
    components.set_result(
        _RESULT_KEY,
        sheet_bytes,
        f"{stem}.{fmt}",
        mime=_MIMES[fmt],
    )
    st.success(
        f"{report.tables_found} tabela(s) extraída(s) de "
        f"{report.pages_with_tables} página(s) — {report.total_rows} linha(s) no total."
    )
