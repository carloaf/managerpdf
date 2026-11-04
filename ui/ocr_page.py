"""Ferramenta: OCR — gera PDF pesquisável a partir de documentos digitalizados."""

from __future__ import annotations

import streamlit as st

from src.ocr import is_ocr_available, make_searchable_pdf
from src.pdf_utils import human_size, safe_stem
from src.preview import render_page_png
from ui import components, theme

_RESULT_KEY = "ocr_result"


def render() -> None:
    theme.hero(
        "🔍",
        "OCR (PDF pesquisável)",
        "Reconheça o texto de documentos digitalizados com IA local e gere "
        "um PDF pesquisável, mantendo a aparência original.",
    )

    if not is_ocr_available():
        st.error(
            "O serviço de OCR não está disponível. Suba a aplicação com "
            "`docker compose up --build` — o container `ocr` inicia junto "
            "com o managerpdf.",
            icon="⚠️",
        )
        theme.footer()
        return

    uploads = components.upload_pdfs(
        "Selecione o PDF digitalizado",
        key="ocr_upload",
        help_text="Ideal para documentos escaneados, sem camada de texto.",
    )
    if not uploads:
        st.info("Envie um PDF digitalizado (escaneado) para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="ocr_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input("ocr_signature", (name, len(data)), _RESULT_KEY)
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    _render_preview(data, password)

    if st.button("🔍 Aplicar OCR", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        _run(data, password, name)

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar PDF pesquisável",
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
        "Reconhecendo o texto com o Indra OCR... (pode levar alguns segundos)"
    ):
        result = components.run_safely(
            make_searchable_pdf, data, password=password
        )

    if result is None:
        return

    pdf_bytes, report = result
    components.set_result(
        _RESULT_KEY,
        pdf_bytes,
        f"{stem}_pesquisavel.pdf",
    )
    st.success(
        f"OCR concluído em {report.elapsed_s:.1f}s — "
        f"{report.pages_ocr} página(s) digitalizada(s) e "
        f"{report.pages_text_layer} já tinha(m) camada de texto."
    )
