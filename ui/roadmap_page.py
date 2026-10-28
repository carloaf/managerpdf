"""Página de roadmap: funcionalidades planejadas (sem implementação ainda)."""

from __future__ import annotations

import streamlit as st

from ui import theme

_PLANNED = [
    (
        "🔍",
        "OCR (reconhecimento de texto)",
        "Aplicar OCR em PDFs digitalizados para gerar documentos "
        "pesquisáveis, mantendo a imagem original como fundo.",
    ),
]


def render() -> None:
    theme.hero(
        "🗺️",
        "Roadmap",
        "Estas ferramentas já estão planejadas. A arquitetura atual foi preparada para recebê-las.",
    )

    theme.card_grid([(icon, title, desc) for icon, title, desc in _PLANNED], columns=1)

    st.write("")
    st.markdown("#### Plano técnico")

    with st.container(border=True):
        st.markdown(
            "**OCR**\n"
            "- Extração de texto nativo primeiro (`page.get_text`) e OCR apenas "
            "quando a página não tiver camada de texto.\n"
            "- Motor sugerido: Tesseract (`pytesseract`) ou `ocrmypdf` na imagem Docker.\n"
            "- Resultado em PDF pesquisável com camada de texto invisível."
        )

    with st.container(border=True):
        st.markdown(
            "**Infra já preparada**\n"
            "- `src/storage.temp_workspace()`: diretório temporário com limpeza "
            "automática, para fluxos que exigem arquivos em disco (ex.: OCR).\n"
            "- `src/preview.py`: renderização de páginas em PNG, já usada nas "
            "prévias de rotação e de conversão em imagens.\n"
            "- `ui/components.run_safely()`: tratamento padronizado de erros."
        )

    st.info(
        "Quer priorizar alguma dessas funcionalidades? Basta pedir que eu "
        "implemente o próximo passo.",
        icon="💡",
    )

    theme.footer()
