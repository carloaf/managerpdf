"""managerpdf — suíte local de ferramentas para PDF (Streamlit + PyMuPDF).

Execução (tudo dentro do container, nada instalado no host):

    docker compose up --build
    # http://localhost:8501
"""

from __future__ import annotations

import streamlit as st

from src.storage import purge_temp_root
from ui import (
    compress_page,
    home,
    image_page,
    merge_page,
    roadmap_page,
    rotate_page,
    split_page,
    theme,
)

st.set_page_config(
    page_title="managerpdf",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Remove sobras de execuções anteriores (o fluxo normal não grava em disco).
purge_temp_root()

theme.apply_theme()

pages = {
    "Ferramentas": [
        st.Page(home.render, title="Início", icon="🏠", url_path="inicio", default=True),
        st.Page(merge_page.render, title="Juntar PDFs", icon="🧩", url_path="juntar"),
        st.Page(split_page.render, title="Dividir PDF", icon="✂️", url_path="dividir"),
        st.Page(rotate_page.render, title="Rotacionar PDF", icon="🔄", url_path="rotacionar"),
        st.Page(compress_page.render, title="Comprimir PDF", icon="🗜️", url_path="comprimir"),
        st.Page(image_page.render, title="PDF para imagem", icon="🖼️", url_path="imagens"),
    ],
    "Em breve": [
        st.Page(roadmap_page.render, title="Roadmap", icon="🗺️", url_path="roadmap"),
    ],
}

st.navigation(pages, position="sidebar").run()

with st.sidebar:
    st.caption("managerpdf · v0.1 · processamento local")
