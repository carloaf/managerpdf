"""Página de roadmap: funcionalidades planejadas (sem implementação ainda)."""

from __future__ import annotations

import streamlit as st

from ui import theme

_PLANNED = [
    (
        "💧",
        "Marca d'água",
        "Adicionar marcas de texto ou imagem às páginas, com controle "
        "de opacidade e posição.",
    ),
    (
        "🔢",
        "Numeração de páginas",
        "Inserir números de página em posições e formatos configuráveis.",
    ),
    (
        "🔐",
        "Proteção por senha",
        "Aplicar senha de abertura (e permissões) ao PDF.",
    ),
    (
        "🧾",
        "Tabelas escaneadas (RapidTable)",
        "Extrair tabelas de PDFs digitalizados com o RapidTable/RapidLayout "
        "(ONNX), complementando a detecção nativa do PyMuPDF.",
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
            "**OCR (implementado ✅)**\n"
            "- Motor: Indra OCR (IA, ONNX Runtime, CPU) em um container Docker "
            "separado (`services/ocr/`).\n"
            "- Páginas com camada de texto são preservadas; as digitalizadas "
            "recebem OCR e uma camada de texto invisível.\n"
            "- `src/ocr.py`: cliente HTTP + reconstrução do PDF pesquisável."
        )

    with st.container(border=True):
        st.markdown(
            "**PDF → Word (implementado ✅)**\n"
            "- Motor: Marker (IA, ONNX Runtime, CPU) em um container separado "
            "(`services/convert/`), seguido de pandoc para gerar o DOCX.\n"
            "- `src/word.py`: cliente HTTP; o PDF é descriptografado localmente."
        )

    with st.container(border=True):
        st.markdown(
            "**PDF → Excel (implementado ✅)**\n"
            "- Motor: `Page.find_tables()` do PyMuPDF (instantâneo, sem IA) para "
            "PDFs digitais; gravação com openpyxl (XLSX) e odfpy (ODS).\n"
            "- `src/excel.py`: extração + geração da planilha.\n"
            "- Próximo passo: RapidTable (ONNX) para tabelas em PDFs escaneados."
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
