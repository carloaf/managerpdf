"""Página inicial: apresentação e atalhos para as ferramentas."""

from __future__ import annotations

import streamlit as st

from ui import theme

_TOOLS = [
    ("🧩", "Juntar PDFs", "Combine vários documentos em um único arquivo, com a ordem que você escolher.", "/juntar"),
    ("✂️", "Dividir PDF", "Separe intervalos de páginas, cada página ou blocos fixos em arquivos novos.", "/dividir"),
    ("🔄", "Rotacionar PDF", "Gire todas as páginas ou apenas as selecionadas em 90°, 180° ou 270°.", "/rotacionar"),
    ("🗜️", "Comprimir PDF", "Reduza o tamanho recompactando imagens e a estrutura do arquivo.", "/comprimir"),
    ("🖼️", "PDF para imagem", "Exporte cada página como JPG/PNG e receba tudo em um ZIP.", "/imagens"),
]

_SOON = [
    ("🔍", "OCR", "Extraia texto de documentos digitalizados e gere PDFs pesquisáveis."),
]


def render() -> None:
    theme.hero(
        "🧾",
        "Todas as suas ferramentas de PDF, no seu computador",
        "Junte, divida, rotacione, comprima e converta arquivos em segundos. "
        "Tudo roda localmente e os arquivos nunca saem da sua máquina.",
    )

    st.markdown("#### Ferramentas disponíveis")
    theme.card_grid(_TOOLS, columns=2)

    st.write("")
    st.markdown("#### Em breve")
    theme.card_grid(_SOON, columns=2)

    st.write("")
    with st.expander("Como funciona", expanded=False):
        st.markdown(
            "1. Escolha a ferramenta no menu lateral ou nos cards da página inicial.\n"
            "2. Envie o PDF (ou vários). Arquivos protegidos por senha são "
            "detectados automaticamente.\n"
            "3. Ajuste as opções e clique no botão de ação.\n"
            "4. Baixe o resultado — o processamento acontece em memória e, "
            "após o download, os arquivos enviados e o resultado são "
            "excluídos do servidor."
        )

    st.info(
        "**Privacidade por padrão:** a aplicação roda no seu próprio "
        "container Docker. Nenhum upload é enviado para serviços externos e "
        "os documentos são excluídos da memória assim que o download do "
        "arquivo processado é concluído.",
        icon="🔒",
    )

    theme.footer()
