"""Compactação de PDFs.

Estratégia em duas frentes:

1. Recompressão das imagens embutidas (redução de resolução + JPEG), usando
   ``Page.replace_image`` do PyMuPDF.
2. Limpeza/compactação da estrutura do arquivo (``garbage``, ``deflate``,
   ``clean``), que remove objetos órfãos e comprime os streams.

Como PDFs com muito texto podem não ganhar espaço, o resultado é comparado
com o original e, se não houver ganho, o arquivo original é devolvido.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import fitz
from PIL import Image

from .pdf_utils import PDFProcessingError, open_pdf

# Ignora imagens muito pequenas: recompressão aqui só piora a qualidade.
_MIN_IMAGE_SIDE = 48

_SAVE_ATTEMPTS: tuple[dict[str, object], ...] = (
    {
        "garbage": 4,
        "deflate": True,
        "deflate_images": True,
        "deflate_fonts": True,
        "clean": True,
    },
    {"garbage": 3, "deflate": True, "deflate_images": True},
    {"garbage": 3, "deflate": True},
)


@dataclass(frozen=True)
class CompressionReport:
    """Resumo do resultado da compactação."""

    original_size: int
    compressed_size: int
    images_optimized: int = 0

    @property
    def saved_bytes(self) -> int:
        return max(self.original_size - self.compressed_size, 0)

    @property
    def saved_percent(self) -> float:
        if self.original_size <= 0:
            return 0.0
        return self.saved_bytes / self.original_size * 100


def compress_pdf(
    data: bytes,
    *,
    image_quality: int = 72,
    max_dpi: int | None = 110,
    grayscale: bool = False,
    password: str | None = None,
) -> tuple[bytes, CompressionReport]:
    """Comprime o PDF e devolve ``(bytes, relatório)``.

    Parâmetros
    ----------
    image_quality:
        Qualidade JPEG (1-100) aplicada às imagens recompressadas.
    max_dpi:
        Resolução máxima das imagens após a conversão; ``None`` mantém a
        resolução original e apenas recompacta.
    grayscale:
        Converte as imagens para escala de cinza (reduz bastante o tamanho).
    """
    if not 1 <= image_quality <= 100:
        raise PDFProcessingError("A qualidade deve estar entre 1 e 100.")

    doc = open_pdf(data, password)
    try:
        images_optimized = _shrink_images(
            doc,
            image_quality=image_quality,
            max_dpi=max_dpi,
            grayscale=grayscale,
        )
        output = _save_with_fallbacks(doc)
    finally:
        doc.close()

    if len(output) >= len(data):
        output = data

    return output, CompressionReport(
        original_size=len(data),
        compressed_size=len(output),
        images_optimized=images_optimized,
    )


def _save_with_fallbacks(doc: fitz.Document) -> bytes:
    """Tenta salvar com o máximo de compactação e vai reduzindo se falhar."""
    last_error: Exception | None = None
    for options in _SAVE_ATTEMPTS:
        try:
            return doc.tobytes(**options)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise PDFProcessingError(
        "Não foi possível compactar este PDF. O arquivo pode estar danificado."
    ) from last_error


def _shrink_images(
    doc: fitz.Document,
    *,
    image_quality: int,
    max_dpi: int | None,
    grayscale: bool,
) -> int:
    """Recomprime as imagens do documento; devolve quantas foram otimizadas."""
    if not hasattr(fitz.Page, "replace_image"):
        return 0

    optimized = 0
    processed: set[int] = set()

    for page in doc:
        try:
            images = page.get_images(full=True)
        except Exception:  # noqa: BLE001
            continue

        for image_info in images:
            xref = image_info[0]
            if xref in processed:
                continue
            processed.add(xref)

            try:
                if _replace_image(
                    doc,
                    page,
                    xref,
                    image_quality=image_quality,
                    max_dpi=max_dpi,
                    grayscale=grayscale,
                ):
                    optimized += 1
            except Exception:  # noqa: BLE001 - imagem problemática: mantém a original
                continue

    return optimized


def _replace_image(
    doc: fitz.Document,
    page: fitz.Page,
    xref: int,
    *,
    image_quality: int,
    max_dpi: int | None,
    grayscale: bool,
) -> bool:
    """Recomprime uma imagem e a substitui na página. ``False`` se não vale a pena."""
    info = doc.extract_image(xref)
    if not info or info.get("smask"):
        # Imagens com máscara de transparência são mantidas como estão.
        return False

    raw: bytes = info["image"]

    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        width, height = image.size
        if width < _MIN_IMAGE_SIDE or height < _MIN_IMAGE_SIDE:
            return False

        target_width = _target_width(page.rect.width, max_dpi)
        resized = target_width is not None and target_width < width

        if resized:
            ratio = target_width / width  # type: ignore[operator]
            image = image.resize(
                (max(1, target_width), max(1, int(height * ratio))),  # type: ignore[arg-type]
                Image.LANCZOS,
            )

        if grayscale:
            image = image.convert("L")
        elif image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=image_quality, optimize=True)

    new_data = buffer.getvalue()

    # Sem redução de resolução e sem ganho real de tamanho: mantém original.
    if not resized and not grayscale and len(new_data) >= len(raw):
        return False

    page.replace_image(xref, stream=new_data)
    return True


def _target_width(page_width_points: float, max_dpi: int | None) -> int | None:
    """Largura em pixels equivalente a ``max_dpi`` para a largura da página."""
    if not max_dpi or page_width_points <= 0:
        return None
    return max(1, int(page_width_points / 72 * max_dpi))
