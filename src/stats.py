"""Contador persistente de trabalhos realizados.

O total é gravado em um arquivo JSON (``STATS_PATH``, padrão
``/data/stats.json``) para sobreviver a reinícios e recriações do container.
Quando o caminho não é gravável (execução sem o volume), o contador continua
funcionando em memória — a página inicial só deixa de acumular entre reinícios.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

# Histórico anterior à criação do contador: a contagem parte de 114.
INITIAL_TOTAL = 114

_DEFAULT_PATH = Path("/data/stats.json")

_lock = threading.Lock()
_cached_total: int | None = None


def _path() -> Path:
    return Path(os.environ.get("STATS_PATH") or _DEFAULT_PATH)


def _load() -> int:
    """Lê o total do disco; qualquer falha resulta no valor inicial."""
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        value = int(raw["total"])
    except (OSError, ValueError, KeyError, TypeError):
        return INITIAL_TOTAL
    return max(INITIAL_TOTAL, value)


def _save(total: int) -> None:
    """Grava o total de forma atômica. Falhas são ignoradas de propósito."""
    path = _path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f"{path.name}.tmp")
        temp.write_text(json.dumps({"total": total}) + "\n", encoding="utf-8")
        temp.replace(path)
    except OSError:
        return


def total() -> int:
    """Total de trabalhos realizados."""
    global _cached_total
    with _lock:
        if _cached_total is None:
            _cached_total = _load()
        return _cached_total


def register_job(count: int = 1) -> int:
    """Soma ``count`` trabalho(s) concluído(s) e devolve o novo total."""
    global _cached_total
    with _lock:
        if _cached_total is None:
            _cached_total = _load()
        _cached_total += max(1, count)
        _save(_cached_total)
        return _cached_total
