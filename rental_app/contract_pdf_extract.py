"""
Phase B5：从 PDF 字节流提取纯文本（文本层），不做 OCR。
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """
    PDF 文本提取逻辑：逐页 extract_text，单页失败则跳过；无文本层则整体可能为空。
    """
    if not file_bytes:
        raise ValueError("empty file")

    from pypdf import PdfReader

    try:
        reader = PdfReader(BytesIO(file_bytes), strict=False)
    except Exception as exc:
        raise ValueError("cannot open as PDF: %s" % exc) from exc

    chunks: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text()
        except Exception:
            # 单页失败不阻断其余页
            t = None
        if t and str(t).strip():
            chunks.append(str(t).strip())

    return "\n\n".join(chunks).strip()


def extract_text_from_pdf(file_path: str | Path) -> str:
    """从本地路径读取 PDF 并提取文本（测试或脚本用）。"""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return extract_text_from_pdf_bytes(path.read_bytes())
