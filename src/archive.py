"""Empacotamento de vários arquivos em um ZIP em memória."""

from __future__ import annotations

import io
import zipfile
from pathlib import PurePosixPath
from typing import Iterable


def build_zip(files: Iterable[tuple[str, bytes]]) -> bytes:
    """Cria um ZIP com os arquivos informados, garantindo nomes únicos.

    Aceita qualquer iterável (inclusive geradores), o que permite empacotar
    imagens à medida que são convertidas, sem manter tudo em memória.
    """
    buffer = io.BytesIO()
    used: set[str] = set()
    written = 0

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(_unique_name(name, used), data)
            written += 1

    if not written:
        raise ValueError("Nenhum arquivo para empacotar.")

    return buffer.getvalue()


def _unique_name(name: str, used: set[str]) -> str:
    """Evita colisões como ``pagina.pdf`` repetido várias vezes no ZIP."""
    candidate = name
    path = PurePosixPath(name)
    counter = 2

    while candidate.lower() in used:
        candidate = f"{path.stem}_{counter}{path.suffix}"
        counter += 1

    used.add(candidate.lower())
    return candidate
