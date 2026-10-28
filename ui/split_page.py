"""Ferramenta: dividir (split) PDF em intervalos, páginas ou blocos."""

from __future__ import annotations

import streamlit as st

from src.archive import build_zip
from src.pdf_utils import (
    PDFProcessingError,
    human_size,
    parse_page_ranges,
    safe_stem,
)
from src.split import PDFPart, extract_ranges, split_every_page, split_in_chunks
from ui import components, theme

_RESULT_KEY = "split_result"

_MODES = (
    "Intervalos personalizados",
    "Uma página por arquivo",
    "Blocos de N páginas",
)


def render() -> None:
    theme.hero(
        "✂️",
        "Dividir PDF",
        "Separe o documento em novos arquivos por intervalo, por página ou em blocos fixos.",
    )

    uploads = components.upload_pdfs("Selecione o arquivo PDF", key="split_upload")
    if not uploads:
        st.info("Envie um PDF para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="split_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input(
        "split_signature", (name, len(data)), _RESULT_KEY
    )
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    mode = st.radio(
        "Como dividir?",
        options=_MODES,
        horizontal=True,
        key="split_mode",
    )

    spec = ""
    combine = False
    chunk_size = 1

    if mode == _MODES[0]:
        spec = st.text_input(
            "Intervalos de páginas",
            value=f"1-{min(3, total)}" if total else "",
            placeholder="Ex.: 1-3, 4-5, 8",
            key="split_ranges",
            help="Use vírgulas para separar intervalos. Páginas isoladas são permitidas.",
        )
        combine = st.checkbox(
            "Juntar todos os intervalos em um único PDF",
            value=False,
            key="split_combine",
        )
    elif mode == _MODES[2]:
        chunk_size = int(
            st.number_input(
                "Páginas por bloco",
                min_value=1,
                max_value=max(1, total),
                value=min(10, max(1, total)),
                step=1,
                key="split_chunk",
            )
        )

    if st.button("✂️ Dividir PDF", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        parts = _run_split(
            mode, data, password, total, name, spec, combine, chunk_size
        )
        if parts:
            _store_parts(parts, name)


def _run_split(
    mode: str,
    data: bytes,
    password: str | None,
    total: int,
    original_name: str,
    spec: str,
    combine: bool,
    chunk_size: int,
) -> list[PDFPart] | None:
    """Valida as opções e executa a divisão escolhida."""
    stem = safe_stem(original_name)

    with st.spinner("Dividindo o PDF..."):
        if mode == _MODES[0]:
            try:
                ranges = parse_page_ranges(spec, total)
            except PDFProcessingError as exc:
                st.error(f"⚠️ {exc}")
                return None
            return components.run_safely(
                extract_ranges,
                data,
                ranges,
                stem=stem,
                password=password,
                combine=combine,
            )

        if mode == _MODES[1]:
            return components.run_safely(
                split_every_page,
                data,
                stem=stem,
                password=password,
            )

        return components.run_safely(
            split_in_chunks,
            data,
            chunk_size,
            stem=stem,
            password=password,
        )


def _store_parts(parts: list[PDFPart], original_name: str) -> None:
    """Guarda o resultado como PDF único ou como ZIP."""
    stem = safe_stem(original_name)

    if len(parts) == 1:
        components.set_result(_RESULT_KEY, parts[0].data, parts[0].filename)
        st.success("Pronto! Um arquivo foi gerado.")
    else:
        zip_bytes = build_zip([(part.filename, part.data) for part in parts])
        components.set_result(
            _RESULT_KEY,
            zip_bytes,
            f"{stem}_dividido.zip",
            mime=components.ZIP_MIME,
        )
        st.success(f"Pronto! {len(parts)} arquivos gerados.")

    _render_table(parts)
    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar resultado",
    )
    theme.footer()


def _render_table(parts: list[PDFPart]) -> None:
    st.dataframe(
        {
            "Arquivo": [part.filename for part in parts],
            "Páginas": [part.page_count for part in parts],
            "Tamanho": [human_size(len(part.data)) for part in parts],
        },
        use_container_width=True,
        hide_index=True,
    )
