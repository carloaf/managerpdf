"""Núcleo de processamento do managerpdf.

Cada módulo expõe funções puras que recebem (e devolvem) ``bytes`` de PDF.
Nenhum arquivo temporário é criado no fluxo normal: tudo acontece em memória,
o que mantém o container leve e elimina a necessidade de limpeza manual.
"""

__all__ = [
    "archive",
    "compress",
    "merge",
    "pdf_utils",
    "preview",
    "rotate",
    "split",
    "storage",
    "to_image",
]
