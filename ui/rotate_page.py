"""Ferramenta: rotacionar páginas de um PDF."""

from __future__ import annotations

import streamlit as st

from src.pdf_utils import (
    PDFProcessingError,
    human_size,
    parse_page_selection,
    safe_stem,
)
from src.preview import render_page_png
from src.rotate import rotate_pdf
from ui import components, theme

_RESULT_KEY = "rotate_result"
_ANGLES = (90, 180, 270)


def render() -> None:
    theme.hero(
        "🔄",
        "Rotacionar PDF",
        "Corrija páginas de cabeça para baixo ou de lado escolhendo o ângulo e o escopo.",
    )

    uploads = components.upload_pdfs("Selecione o arquivo PDF", key="rotate_upload")
    if not uploads:
        st.info("Envie um PDF para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="rotate_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input(
        "rotate_signature", (name, len(data)), _RESULT_KEY
    )
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    col_angle, col_scope = st.columns([1, 1])
    angle = col_angle.radio(
        "Ângulo de rotação",
        options=_ANGLES,
        horizontal=True,
        format_func=lambda value: f"{value}°",
        key="rotate_angle",
    )
    scope = col_scope.radio(
        "Aplicar em",
        options=("Todas as páginas", "Páginas selecionadas"),
        horizontal=True,
        key="rotate_scope",
    )

    spec = ""
    if scope == "Páginas selecionadas":
        spec = st.text_input(
            "Páginas",
            placeholder="Ex.: 1, 3, 5-7",
            key="rotate_pages",
            help="Aceita páginas isoladas e intervalos, separados por vírgula.",
        )

    _render_preview(data, password, angle)

    if st.button("🔄 Rotacionar PDF", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        result = _apply(data, password, angle, scope, spec, total, name)
        if result:
            components.set_result(
                _RESULT_KEY,
                result,
                f"{safe_stem(name)}_rotacionado.pdf",
            )
            st.success("Rotação aplicada com sucesso.")

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar PDF rotacionado",
    )
    theme.footer()


def _render_preview(data: bytes, password: str | None, angle: int) -> None:
    """Comparação lado a lado da página 1 (original vs. rotacionada)."""
    try:
        original = render_page_png(data, 0, dpi=70, password=password)
        rotated = render_page_png(data, 0, dpi=70, rotation=angle, password=password)
    except Exception:  # noqa: BLE001 - prévia é opcional
        return

    left, right = st.columns(2)
    left.image(original, caption="Página 1 — original", use_container_width=True)
    right.image(
        rotated,
        caption=f"Página 1 — após {angle}°",
        use_container_width=True,
    )


def _apply(
    data: bytes,
    password: str | None,
    angle: int,
    scope: str,
    spec: str,
    total: int,
    name: str,
) -> bytes | None:
    pages: list[int] | None = None

    if scope == "Páginas selecionadas":
        try:
            pages = parse_page_selection(spec, total)
        except PDFProcessingError as exc:
            st.error(f"⚠️ {exc}")
            return None

    with st.spinner("Rotacionando páginas..."):
        return components.run_safely(
            rotate_pdf,
            data,
            angle,
            pages,
            password=password,
        )
