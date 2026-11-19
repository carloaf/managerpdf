"""Ferramenta: converter PDF para Word (DOCX) com o Marker (IA em CPU)."""

from __future__ import annotations

import streamlit as st

from src.pdf_utils import human_size, safe_stem
from src.preview import render_page_png
from src.word import is_word_available, pdf_to_docx
from ui import components, theme

_RESULT_KEY = "word_result"

_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def render() -> None:
    theme.hero(
        "📄",
        "PDF para Word",
        "Converta o PDF em um documento DOCX editável, preservando a ordem "
        "de leitura, títulos, listas e tabelas com IA local (Marker, CPU).",
    )

    if not is_word_available():
        st.error(
            "O serviço de conversão não está disponível. Suba a aplicação "
            "com `docker compose up --build` — o container `convert` inicia "
            "junto com o managerpdf.",
            icon="⚠️",
        )
        theme.footer()
        return

    uploads = components.upload_pdfs(
        "Selecione o arquivo PDF",
        key="word_upload",
        help_text="O documento é processado localmente e convertido em DOCX.",
    )
    if not uploads:
        st.info("Envie um PDF para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="word_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input("word_signature", (name, len(data)), _RESULT_KEY)
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    _render_preview(data, password)

    st.info(
        "A conversão usa o Marker em modo CPU (`fast`): boa fidelidade de "
        "estrutura sem exigir GPU. Documentos escaneados também recebem OCR.",
        icon="🧠",
    )

    if st.button("📄 Converter para Word", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        _run(data, password, name)

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar DOCX",
        caption="O resultado é um documento Word editável (.docx).",
    )
    theme.footer()


def _render_preview(data: bytes, password: str | None) -> None:
    """Miniatura da primeira página para conferir o documento enviado."""
    try:
        preview = render_page_png(data, 0, dpi=70, password=password)
    except Exception:  # noqa: BLE001 - prévia é opcional
        return
    st.image(preview, caption="Prévia da página 1", width=320)


def _run(data: bytes, password: str | None, name: str) -> None:
    stem = safe_stem(name)
    with st.spinner(
        "Convertendo com o Marker... (pode levar alguns segundos por página)"
    ):
        result = components.run_safely(pdf_to_docx, data, password=password)

    if result is None:
        return

    docx_bytes, report = result
    components.set_result(
        _RESULT_KEY,
        docx_bytes,
        f"{stem}.docx",
        mime=_DOCX_MIME,
    )
    st.success(f"Conversão concluída em {report.elapsed_s:.1f}s.")
