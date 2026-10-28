"""Componentes reutilizáveis de interface (upload, senha, resultado)."""

from __future__ import annotations

from typing import Any, Callable, Sequence, TypeVar

import streamlit as st

from src.pdf_utils import (
    PDFPasswordError,
    PDFProcessingError,
    human_size,
    open_pdf,
)

PDF_MIME = "application/pdf"
ZIP_MIME = "application/zip"

# Ao baixar (ou descartar) um resultado, os uploads e o arquivo gerado saem da
# memória. O token recria os widgets de upload e a mensagem é exibida no rerun.
_PURGE_TOKEN_KEY = "_mp_purge_token"
_PURGE_NOTICE_KEY = "_mp_purge_notice"

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Upload e validação
# ---------------------------------------------------------------------------
def upload_pdfs(
    label: str,
    *,
    key: str,
    multiple: bool = False,
    help_text: str | None = None,
) -> list[Any]:
    """Uploader de PDFs que sempre devolve uma lista de arquivos."""
    _render_purge_notice()
    uploads = st.file_uploader(
        label,
        type=["pdf"],
        accept_multiple_files=multiple,
        key=_uploader_key(key),
        help=help_text,
    )
    if uploads is None:
        return []
    if isinstance(uploads, list):
        return uploads
    return [uploads]


def _uploader_key(key: str) -> str:
    """Inclui o token de limpeza para que o uploader seja recriado vazio."""
    token = st.session_state.get(_PURGE_TOKEN_KEY, 0)
    return f"{key}::{token}"


def _render_purge_notice() -> None:
    message = st.session_state.pop(_PURGE_NOTICE_KEY, None)
    if message:
        st.success(message, icon="🧹")


def _purge(message: str, *state_keys: str) -> None:
    """Remove resultados da sessão e força a recriação dos uploaders."""
    for key in state_keys:
        st.session_state.pop(key, None)
    _delete_uploads()
    st.session_state[_PURGE_TOKEN_KEY] = st.session_state.get(_PURGE_TOKEN_KEY, 0) + 1
    st.session_state[_PURGE_NOTICE_KEY] = message


def _delete_uploads() -> None:
    """Libera os bytes dos uploads guardados pelo runtime do Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        if ctx is not None:
            ctx.uploaded_file_mgr.remove_session_files(ctx.session_id)
    except Exception:  # noqa: BLE001 - API interna: falha não deve quebrar a limpeza
        return


def _on_download(*state_keys: str) -> None:
    """Callback do download: descarta o resultado e os uploads da memória."""
    _purge(
        "Download iniciado. Os arquivos enviados e o resultado foram "
        "excluídos da memória do servidor.",
        *state_keys,
    )


def resolve_pdf(
    file: Any,
    *,
    password_key: str,
) -> tuple[str, bytes, str | None] | None:
    """Valida um upload e, se necessário, solicita a senha do arquivo.

    Devolve ``(nome, bytes, senha)`` ou ``None`` quando o arquivo não pode ser
    usado ainda (senha pendente ou arquivo inválido).
    """
    data: bytes = file.getvalue()
    name: str = file.name

    try:
        _validate(data, None, name)
        return name, data, None
    except PDFPasswordError:
        pass  # tratamento abaixo
    except PDFProcessingError as exc:
        st.error(str(exc))
        return None

    password = st.text_input(
        f"Senha de “{name}”",
        type="password",
        key=f"{password_key}::{name}::{len(data)}",
        help="Arquivos protegidos só podem ser processados com a senha correta.",
    )
    if not password:
        st.info(f"“{name}” está protegido por senha. Informe a senha para continuar.")
        return None

    try:
        _validate(data, password, name)
    except PDFProcessingError as exc:
        st.error(str(exc))
        return None

    return name, data, password


def _validate(data: bytes, password: str | None, name: str) -> int:
    doc = open_pdf(data, password, filename=name)
    try:
        return doc.page_count
    finally:
        doc.close()


def page_count(data: bytes, password: str | None = None) -> int | None:
    """Quantidade de páginas, sem levantar erro para a interface."""
    try:
        return _validate(data, password, "documento.pdf")
    except PDFProcessingError:
        return None


# ---------------------------------------------------------------------------
# Execução segura
# ---------------------------------------------------------------------------
def run_safely(func: Callable[..., T], *args: Any, **kwargs: Any) -> T | None:
    """Executa ``func`` convertendo falhas conhecidas em mensagens amigáveis."""
    try:
        return func(*args, **kwargs)
    except PDFProcessingError as exc:
        st.error(f"⚠️ {exc}")
    except Exception as exc:  # noqa: BLE001 - última barreira da interface
        st.error(f"⚠️ Erro inesperado ao processar o arquivo: {exc}")
    return None


# ---------------------------------------------------------------------------
# Resultado (guardado na sessão para sobreviver aos reruns do Streamlit)
# ---------------------------------------------------------------------------
def set_result(
    state_key: str,
    data: bytes,
    filename: str,
    *,
    mime: str = PDF_MIME,
) -> None:
    st.session_state[state_key] = {
        "data": data,
        "filename": filename,
        "mime": mime,
    }


def show_result(
    state_key: str,
    *,
    download_label: str = "⬇️ Baixar arquivo",
    caption: str | None = None,
    clear_keys: Sequence[str] = (),
) -> None:
    """Exibe o botão de download do resultado atual e opção de limpar."""
    result = st.session_state.get(state_key)
    if not result:
        return

    st.divider()
    st.subheader("Pronto! 🎉")
    if caption:
        st.caption(caption)

    left, right = st.columns([3, 1], vertical_alignment="bottom")
    left.download_button(
        download_label,
        data=result["data"],
        file_name=result["filename"],
        mime=result["mime"],
        type="primary",
        use_container_width=True,
        key=f"{state_key}__download",
        on_click=_on_download,
        args=(state_key, *clear_keys),
    )
    if right.button(
        "Descartar",
        key=f"{state_key}__clear",
        use_container_width=True,
    ):
        _purge(
            "Resultado descartado. Os arquivos enviados e o resultado foram "
            "excluídos da memória do servidor.",
            state_key,
            *clear_keys,
        )
        st.rerun()

    st.caption(
        f"`{result['filename']}` · {human_size(len(result['data']))}"
    )
    st.caption(
        "🔒 Ao baixar o arquivo, os uploads e o resultado são excluídos "
        "da memória do servidor."
    )


def clear_result(*state_keys: str) -> None:
    for key in state_keys:
        st.session_state.pop(key, None)


def reset_on_new_input(
    signature_key: str,
    signature: Any,
    *result_keys: str,
) -> None:
    """Descarta resultados antigos quando o arquivo de entrada muda.

    Evita que o usuário baixe um resultado gerado a partir de outro upload.
    """
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        clear_result(*result_keys)
