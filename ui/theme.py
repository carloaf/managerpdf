"""Tema visual: CSS global, cabeçalho (hero) e cartões."""

from __future__ import annotations

from typing import Sequence

import streamlit as st

_CSS = """
<style>
  :root {
    --mp-accent: #e11d48;
    --mp-accent-2: #f97316;
    --mp-ink: #0f172a;
    --mp-muted: #64748b;
    --mp-border: #e2e8f0;
    --mp-soft: #f8fafc;
  }

  .block-container { padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1120px; }
  header[data-testid="stHeader"] { background: transparent; }

  /* Hero */
  .mp-hero {
    background: linear-gradient(135deg, var(--mp-accent) 0%, var(--mp-accent-2) 100%);
    border-radius: 22px;
    padding: 2.1rem 2rem 1.9rem;
    color: #fff;
    margin-bottom: 1.6rem;
    box-shadow: 0 22px 45px -26px rgba(225, 29, 72, 0.85);
  }
  .mp-hero .mp-badge {
    display: inline-block;
    background: rgba(255, 255, 255, 0.18);
    padding: 0.22rem 0.65rem;
    border-radius: 999px;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.85rem;
  }
  .mp-hero h1 {
    font-size: clamp(1.6rem, 3vw, 2.1rem);
    line-height: 1.15;
    margin: 0 0 0.5rem 0;
    color: #fff;
    font-weight: 700;
  }
  .mp-hero p { margin: 0; font-size: 0.98rem; opacity: 0.94; max-width: 62ch; }

  /* Cartões */
  .mp-card {
    background: #fff;
    border: 1px solid var(--mp-border);
    border-radius: 16px;
    padding: 1.05rem 1.15rem;
    height: 100%;
    box-shadow: 0 10px 24px -16px rgba(15, 23, 42, 0.38),
                0 2px 6px rgba(15, 23, 42, 0.06);
  }
  .mp-card .mp-card-icon { font-size: 1.45rem; line-height: 1; }
  .mp-card h3 { margin: 0.55rem 0 0.3rem; font-size: 1rem; color: var(--mp-ink); }
  .mp-card p { margin: 0; font-size: 0.875rem; color: var(--mp-muted); line-height: 1.45; }
  .mp-card.mp-soon { background: var(--mp-soft); border-style: dashed; }

  /* Cards clicáveis (atalhos da página inicial) */
  .mp-card .mp-card-title {
    display: block;
    margin: 0.55rem 0 0.3rem;
    font-size: 1rem;
    font-weight: 700;
    color: var(--mp-ink);
  }
  .mp-card .mp-card-desc {
    display: block;
    font-size: 0.875rem;
    color: var(--mp-muted);
    line-height: 1.45;
  }
  a.mp-card {
    display: block;
    color: inherit;
    text-decoration: none;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  }
  a.mp-card:hover {
    border-color: var(--mp-accent);
    box-shadow: 0 20px 36px -18px rgba(225, 29, 72, 0.55),
                0 4px 12px rgba(15, 23, 42, 0.08);
    transform: translateY(-2px);
  }
  a.mp-card:focus-visible {
    outline: 2px solid var(--mp-accent);
    outline-offset: 2px;
  }
  a.mp-card .mp-card-cta {
    display: inline-block;
    margin-top: 0.7rem;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--mp-accent);
  }

  /* Linhas de arquivo (ordenação do merge) */
  .mp-file {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.9rem;
    color: var(--mp-ink);
    overflow: hidden;
  }
  .mp-file .mp-index {
    flex: none;
    width: 1.55rem; height: 1.55rem;
    display: grid; place-items: center;
    border-radius: 8px;
    background: #f1f5f9;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--mp-muted);
  }
  .mp-file .mp-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* Ajustes de componentes nativos */
  [data-testid="stFileUploaderDropzone"] {
    border: 2px dashed #cbd5e1;
    border-radius: 16px;
    background: var(--mp-soft);
    padding: 1.1rem;
  }
  [data-testid="stSidebar"] {
    background: var(--mp-soft);
    border-right: 1px solid var(--mp-border);
  }
  div.stButton > button, div.stDownloadButton > button {
    border-radius: 10px;
    font-weight: 600;
  }
  div.stButton > button[kind="primary"],
  div.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--mp-accent), var(--mp-accent-2));
    border: none;
    color: #fff;
  }
  [data-testid="stMetricValue"] { font-size: 1.35rem; }
  .mp-footer {
    margin-top: 2.2rem;
    padding-top: 0.9rem;
    border-top: 1px solid var(--mp-border);
    color: var(--mp-muted);
    font-size: 0.78rem;
    text-align: center;
  }
</style>
"""


def apply_theme() -> None:
    """Injeta o CSS global. Deve ser chamado uma vez por rerun do app."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(icon: str, title: str, subtitle: str) -> None:
    """Cabeçalho em gradiente usado no topo de cada ferramenta."""
    st.markdown(
        f"""
        <div class="mp-hero">
          <span class="mp-badge">{icon} managerpdf</span>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(
    icon: str,
    title: str,
    description: str,
    *,
    soon: bool = False,
    url: str | None = None,
) -> str:
    """HTML de um cartão de ferramenta (para uso com ``st.markdown``).

    Quando ``url`` é informado, o cartão inteiro vira um link para a
    ferramenta correspondente.
    """
    extra = " mp-soon" if soon else ""
    if url:
        # Apenas elementos inline dentro do <a>: o parser de Markdown do
        # Streamlit quebraria a âncora se houvesse elementos de bloco aqui.
        return (
            f'<a class="mp-card{extra} mp-card-link" href="{url}" target="_self">'
            f'<span class="mp-card-icon">{icon}</span>'
            f'<span class="mp-card-title">{title}</span>'
            f'<span class="mp-card-desc">{description}</span>'
            '<span class="mp-card-cta">Abrir ferramenta →</span>'
            "</a>"
        )

    return (
        f'<div class="mp-card{extra}">'
        f'<div class="mp-card-icon">{icon}</div>'
        f"<h3>{title}</h3>"
        f"<p>{description}</p>"
        "</div>"
    )


def card_grid(
    cards: Sequence[tuple[str, str, str] | tuple[str, str, str, str]],
    *,
    columns: int = 3,
) -> None:
    """Distribui cartões em uma grade com ordem de leitura natural (linha a linha).

    Um quarto item opcional no cartão define a URL de navegação.
    """
    for start in range(0, len(cards), columns):
        row = st.columns(columns)
        for column, item in zip(row, cards[start : start + columns]):
            icon, title, description, *rest = item
            url = rest[0] if rest else None
            with column:
                st.markdown(
                    card(icon, title, description, url=url),
                    unsafe_allow_html=True,
                )
        st.write("")


def footer(
    text: str = (
        "managerpdf · processamento 100% local, na sua máquina · "
        "documentos excluídos após o download"
    ),
) -> None:
    st.markdown(f'<div class="mp-footer">{text}</div>', unsafe_allow_html=True)
