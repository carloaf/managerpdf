"""Ferramenta: converter páginas de um PDF em imagens JPG/PNG."""

from __future__ import annotations

import streamlit as st

from src.archive import build_zip
from src.pdf_utils import (
    PDFProcessingError,
    human_size,
    parse_page_selection,
    safe_stem,
)
from src.preview import render_page_png
from src.to_image import iter_page_images
from ui import components, theme

_RESULT_KEY = "image_result"

_FORMATS = {
    "PNG — sem perdas": "png",
    "JPG — arquivo menor": "jpg",
}

_DPI_OPTIONS = {
    72: "72 DPI — rascunho",
    120: "120 DPI — leve",
    150: "150 DPI — recomendado",
    200: "200 DPI — nítido",
    300: "300 DPI — alta qualidade",
}

_ALL_PAGES = "Todas as páginas"
_SELECTED_PAGES = "Páginas selecionadas"


def render() -> None:
    theme.hero(
        "🖼️",
        "PDF para imagem",
        "Transforme cada página em JPG ou PNG e receba todas as imagens em um arquivo ZIP.",
    )

    uploads = components.upload_pdfs("Selecione o arquivo PDF", key="image_upload")
    if not uploads:
        st.info("Envie um PDF para começar.")
        theme.footer()
        return

    resolved = components.resolve_pdf(uploads[0], password_key="image_pwd")
    if resolved is None:
        theme.footer()
        return

    name, data, password = resolved
    total = components.page_count(data, password) or 0
    components.reset_on_new_input(
        "image_signature", (name, len(data)), _RESULT_KEY
    )
    st.caption(f"`{name}` · {total} páginas · {human_size(len(data))}")
    st.divider()

    fmt_label, dpi, quality, scope, spec = _render_options(total)
    _render_preview(data, password)

    if st.button("🖼️ Converter em imagens", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        _convert(data, password, name, total, fmt_label, dpi, quality, scope, spec)

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar ZIP com as imagens",
    )
    theme.footer()


def _render_options(total: int) -> tuple[str, int, int, str, str]:
    with st.container(border=True):
        st.markdown("**Opções de conversão**")
        col_format, col_dpi = st.columns(2)
        fmt_label = col_format.selectbox(
            "Formato",
            options=list(_FORMATS),
            index=0,
            key="image_format",
        )
        dpi = int(
            col_dpi.selectbox(
                "Resolução",
                options=list(_DPI_OPTIONS),
                index=2,
                format_func=lambda value: _DPI_OPTIONS[value],
                key="image_dpi",
                help="Resoluções maiores geram imagens mais nítidas e arquivos maiores.",
            )
        )

        quality = 90
        if _FORMATS[fmt_label] == "jpg":
            quality = int(
                st.slider(
                    "Qualidade JPG",
                    min_value=40,
                    max_value=100,
                    value=90,
                    step=1,
                    key="image_quality",
                    help="Qualidade menor gera imagens mais leves, com mais artefatos.",
                )
            )

        scope = st.radio(
            "Páginas",
            options=(_ALL_PAGES, _SELECTED_PAGES),
            horizontal=True,
            key="image_scope",
        )

        spec = ""
        if scope == _SELECTED_PAGES:
            spec = st.text_input(
                "Intervalos de páginas",
                value=f"1-{total}" if total else "",
                placeholder="Ex.: 1, 3, 5-7",
                key="image_pages",
                help="Aceita páginas isoladas e intervalos, separados por vírgula.",
            )

    st.caption(
        "Cada página vira um arquivo separado dentro do ZIP. "
        "A prévia abaixo não representa a resolução final."
    )

    return fmt_label, dpi, quality, scope, spec


def _render_preview(data: bytes, password: str | None) -> None:
    """Miniatura da primeira página para conferir o documento enviado."""
    try:
        preview = render_page_png(data, 0, dpi=70, password=password)
    except Exception:  # noqa: BLE001 - prévia é opcional
        return

    st.image(preview, caption="Prévia da página 1", width=320)


def _convert(
    data: bytes,
    password: str | None,
    name: str,
    total: int,
    fmt_label: str,
    dpi: int,
    quality: int,
    scope: str,
    spec: str,
) -> None:
    pages: list[int] | None = None
    if scope == _SELECTED_PAGES:
        try:
            pages = parse_page_selection(spec, total)
        except PDFProcessingError as exc:
            st.error(f"⚠️ {exc}")
            return

    fmt = _FORMATS[fmt_label]
    stem = safe_stem(name)

    with st.spinner("Convertendo as páginas em imagens..."):
        zip_bytes = components.run_safely(
            _build_images_zip,
            data,
            password=password,
            fmt=fmt,
            dpi=dpi,
            quality=quality,
            pages=pages,
            stem=stem,
        )

    if not zip_bytes:
        return

    count = len(pages) if pages is not None else total
    components.set_result(
        _RESULT_KEY,
        zip_bytes,
        f"{stem}_imagens.zip",
        mime=components.ZIP_MIME,
    )
    st.success(f"{count} página(s) convertida(s) em {fmt.upper()}.")


def _build_images_zip(
    data: bytes,
    *,
    password: str | None,
    fmt: str,
    dpi: int,
    quality: int,
    pages: list[int] | None,
    stem: str,
) -> bytes:
    images = iter_page_images(
        data,
        fmt=fmt,
        dpi=dpi,
        quality=quality,
        pages=pages,
        stem=stem,
        password=password,
    )
    return build_zip((image.filename, image.data) for image in images)
