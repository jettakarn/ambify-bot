"""RapidOCR wrapper for roster page images."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


@dataclass(frozen=True)
class OcrBox:
    """One OCR text detection with center coordinates."""

    text: str
    x: float
    y: float
    confidence: float


@lru_cache(maxsize=1)
def _engine() -> RapidOCR:
    return RapidOCR()


def run_ocr(image_path: Path) -> list[OcrBox]:
    """Run OCR on an image and return text boxes with center coordinates."""
    result, _elapsed = _engine()(str(image_path))
    if not result:
        return []

    boxes: list[OcrBox] = []
    for item in result:
        bbox, text, score = item[0], item[1], float(item[2])
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        cleaned = str(text).strip()
        if not cleaned:
            continue
        boxes.append(
            OcrBox(
                text=cleaned,
                x=sum(xs) / len(xs),
                y=sum(ys) / len(ys),
                confidence=score,
            )
        )
    return boxes
