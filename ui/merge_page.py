"""Ferramenta: juntar (merge) PDFs, com controle de ordem dos arquivos."""

from __future__ import annotations

import streamlit as st

from src.merge import merge_pdfs
from src.pdf_utils import human_size, safe_stem
from ui import components, theme

_RESULT_KEY = "merge_result"
_ORDER_KEY = "merge_order"
_SIGNATURE_KEY = "merge_signature"


def render() -> None:
    theme.hero(
        "🧩",
        "Juntar PDFs",
        "Envie dois ou mais documentos e defina a ordem final das páginas.",
    )

    uploads = components.upload_pdfs(
        "Selecione os arquivos PDF",
        key="merge_upload",
        multiple=True,
        help_text="Arraste os arquivos ou clique para selecionar. Máx. 200 MB por arquivo.",
    )

    if not uploads:
        st.info("Envie ao menos dois arquivos PDF para começar.")
        theme.footer()
        return

    _sync_order(uploads)
    order = _render_order(uploads)

    if len(order) < 2:
        st.warning("Mantenha ao menos dois arquivos na lista para juntar.")
        theme.footer()
        return

    resolved = _resolve_files([uploads[index] for index in order])
    if resolved is None:
        theme.footer()
        return

    total_size = sum(len(data) for _, data, _ in resolved)
    pages = sum(components.page_count(data, pwd) or 0 for _, data, pwd in resolved)
    st.caption(
        f"**{len(resolved)} arquivos** · {pages} páginas · {human_size(total_size)}"
    )

    if st.button("🧩 Juntar PDFs", type="primary", use_container_width=True):
        st.session_state.pop(_RESULT_KEY, None)
        with st.spinner("Juntando documentos..."):
            result = components.run_safely(
                merge_pdfs,
                [(name, data) for name, data, _ in resolved],
                {name: pwd for name, _, pwd in resolved if pwd},
            )
        if result:
            first_stem = safe_stem(resolved[0][0])
            components.set_result(_RESULT_KEY, result, f"{first_stem}_unido.pdf")
            st.success(f"Pronto! {len(resolved)} arquivos combinados.")

    components.show_result(
        _RESULT_KEY,
        download_label="⬇️ Baixar PDF unido",
    )
    theme.footer()


# ---------------------------------------------------------------------------
# Ordenação
# ---------------------------------------------------------------------------
def _sync_order(uploads: list) -> None:
    """Recria a ordem sempre que o conjunto de uploads mudar."""
    signature = tuple((file.name, file.size) for file in uploads)
    if st.session_state.get(_SIGNATURE_KEY) != signature:
        st.session_state[_SIGNATURE_KEY] = signature
        st.session_state[_ORDER_KEY] = list(range(len(uploads)))
        components.clear_result(_RESULT_KEY)


def _render_order(uploads: list) -> list[int]:
    order: list[int] = st.session_state[_ORDER_KEY]

    with st.container(border=True):
        st.markdown("**Ordem dos arquivos**")
        st.caption("Use as setas para reorganizar. O PDF final segue esta ordem.")

        for position, index in enumerate(list(order)):
            col_num, col_name, col_up, col_down = st.columns(
                [0.5, 6, 0.55, 0.55], vertical_alignment="center"
            )
            col_num.markdown(
                f'<div class="mp-file"><span class="mp-index">{position + 1}</span></div>',
                unsafe_allow_html=True,
            )
            col_name.markdown(
                f'<div class="mp-file"><span class="mp-name">{uploads[index].name}</span></div>',
                unsafe_allow_html=True,
            )
            if col_up.button(
                "▲",
                key=f"merge_up_{index}",
                disabled=position == 0,
                use_container_width=True,
                help="Mover para cima",
            ):
                order[position - 1], order[position] = order[position], order[position - 1]
                st.rerun()
            if col_down.button(
                "▼",
                key=f"merge_down_{index}",
                disabled=position == len(order) - 1,
                use_container_width=True,
                help="Mover para baixo",
            ):
                order[position + 1], order[position] = order[position], order[position + 1]
                st.rerun()

        st.write("")
        col_sort, col_reverse = st.columns(2)
        if col_sort.button("Ordenar por nome", use_container_width=True):
            st.session_state[_ORDER_KEY] = sorted(
                order, key=lambda i: uploads[i].name.lower()
            )
            st.rerun()
        if col_reverse.button("Inverter ordem", use_container_width=True):
            st.session_state[_ORDER_KEY] = list(reversed(order))
            st.rerun()

    return st.session_state[_ORDER_KEY]


# ---------------------------------------------------------------------------
# Validação de senha
# ---------------------------------------------------------------------------
def _resolve_files(
    files: list,
) -> list[tuple[str, bytes, str | None]] | None:
    resolved: list[tuple[str, bytes, str | None]] = []
    for file in files:
        item = components.resolve_pdf(file, password_key="merge_pwd")
        if item is None:
            return None
        resolved.append(item)
    return resolved
