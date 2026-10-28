"""Ferramenta: comprimir PDF."""

from __future__ import annotations

import streamlit as st

from src.compress import CompressionReport, compress_pdf
from src.pdf_utils import human_size, safe_stem
from ui import components, theme

_RESULT_KEY = "compress_result"
_REPORT_KEY = "compress_report"

_DPI_OPTIONS = {
    "72 DPI — menor arquivo": 72,
    "96 DPI — equilíbrio": 96,
    "110 DPI — recomendado": 110,
    "150 DPI — mais nitidez": 150,
    "Manter resolução original": None,
}


def render() -> None:
    theme.hero(
        "🗜️",
        "Comprimir PDF",
        "Reduza o tamanho do arquivo recomprimindo imagens e limpando a estrutura do PDF.",
    )

    uploads = components.upload_pdfs("Selecione o arquivo PDF", key="compress_upload")
    if not uploads:
        st.info("Envie um PDF para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="compress_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input(
        "compress_signature", (name, len(data)), _RESULT_KEY, _REPORT_KEY
    )
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    with st.container(border=True):
        st.markdown("**Opções de compressão**")
        quality = st.slider(
            "Qualidade das imagens (JPEG)",
            min_value=30,
            max_value=95,
            value=72,
            step=1,
            key="compress_quality",
            help="Qualidade menor gera arquivos menores, com mais artefatos visuais.",
        )
        dpi_label = st.selectbox(
            "Resolução máxima das imagens",
            options=list(_DPI_OPTIONS),
            index=2,
            key="compress_dpi",
        )
        grayscale = st.checkbox(
            "Converter imagens para escala de cinza",
            value=False,
            key="compress_gray",
            help="Reduz bastante o tamanho em documentos com fotos ou digitalizações.",
        )

    st.caption(
        "A estrutura do arquivo também é limpa (objetos órfãos removidos e "
        "streams compactados). PDFs somente texto podem ganhar pouco espaço."
    )

    if st.button("🗜️ Comprimir PDF", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        st.session_state.pop(_REPORT_KEY, None)

        with st.spinner("Comprimindo o PDF..."):
            outcome = components.run_safely(
                compress_pdf,
                data,
                image_quality=quality,
                max_dpi=_DPI_OPTIONS[dpi_label],
                grayscale=grayscale,
                password=password,
            )

        if outcome:
            result, report = outcome
            components.set_result(
                _RESULT_KEY,
                result,
                f"{safe_stem(name)}_comprimido.pdf",
            )
            st.session_state[_REPORT_KEY] = report
            st.success("Compressão concluída.")

    _render_report(st.session_state.get(_REPORT_KEY))

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar PDF comprimido",
        clear_keys=(_REPORT_KEY,),
    )
    theme.footer()


def _render_report(report: CompressionReport | None) -> None:
    if report is None:
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Tamanho original", human_size(report.original_size))
    col2.metric("Tamanho final", human_size(report.compressed_size))
    col3.metric("Redução", f"{report.saved_percent:.0f}%")

    if report.images_optimized:
        st.caption(f"🖼️ {report.images_optimized} imagem(ns) otimizada(s).")

    if report.saved_bytes == 0:
        st.warning(
            "Este PDF já estava otimizado: não foi possível reduzir o tamanho. "
            "O arquivo original será mantido no download."
        )
