"""Gestão de arquivos temporários.

O managerpdf processa tudo em memória (``bytes``), então o fluxo normal não
grava nada em disco. Este módulo existe para:

* oferecer um diretório de trabalho seguro (com limpeza automática) para
  funcionalidades futuras que exigem arquivos reais em disco, como OCR;
* varrer e remover sobras de execuções anteriores em ``/tmp/managerpdf``,
  evitando que o container cresça indefinidamente.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

TEMP_ROOT = Path(tempfile.gettempdir()) / "managerpdf"


def purge_temp_root(max_age_hours: float = 6.0) -> int:
    """Remove diretórios/arquivos temporários antigos. Devolve quantos removeu."""
    if not TEMP_ROOT.exists():
        return 0

    cutoff = time.time() - max_age_hours * 3600
    removed = 0

    for entry in TEMP_ROOT.iterdir():
        try:
            if entry.stat().st_mtime > cutoff:
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
            removed += 1
        except OSError:
            # Item em uso ou sem permissão: ignora e segue.
            continue

    return removed


@contextmanager
def temp_workspace(prefix: str = "job-") -> Iterator[Path]:
    """Diretório temporário cujo conteúdo é apagado ao sair do bloco ``with``."""
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=TEMP_ROOT))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
