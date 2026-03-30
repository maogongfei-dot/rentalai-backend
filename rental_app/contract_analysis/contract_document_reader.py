"""
Phase 3 Part 4：合同文档读取 / 文本提取（最小可运行版）。

- TXT：多编码读取。
- PDF：优先 ``pypdf``，否则 ``PyPDF2``；逐页 ``extract_text`` 后拼接（文本层，非 OCR）。
- DOCX：``python-docx``（``import docx``）段落拼接。

失败时主流程不抛异常：``extract_contract_text`` 返回空字符串；
需要原因时使用 ``extract_contract_text_outcome``（``ContractReadOutcome``）。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, TypedDict

from .contract_models import ContractSourceType, coerce_contract_source_type

logger = logging.getLogger(__name__)


class ContractReadOutcome(TypedDict, total=False):
    """文档读取结果：``text`` 为清洗后的正文；失败时 ``text`` 为空且 ``error`` 非空。"""

    text: str
    error: str | None


def _as_path(file_path: str | os.PathLike[str]) -> Path:
    return Path(file_path).expanduser()


def _clean_extracted_text(s: str) -> str:
    """
    轻量清洗：统一换行、行尾空白、合并行内多余空格、将 3 个以上连续换行压成两段。
    """
    if not s:
        return ""
    t = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]
    t = "\n".join(lines)
    t = re.sub(r"\n{3,}", "\n\n", t)

    def _collapse_spaces(line: str) -> str:
        return re.sub(r"[ \t]{2,}", " ", line)

    t = "\n".join(_collapse_spaces(ln) for ln in t.split("\n"))
    return t.strip()


def _resolve_pdf_reader() -> tuple[Callable[..., Any] | None, str | None]:
    """返回 ``(PdfReader 类, None)``，或 ``(None, 错误说明)``。"""
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]

        return PdfReader, None
    except ImportError:
        pass
    try:
        from PyPDF2 import PdfReader  # type: ignore[import-untyped]

        return PdfReader, None
    except ImportError:
        return None, "未安装 PDF 库：请执行 pip install pypdf（或 PyPDF2）"


def read_contract_from_txt(file_path: str | os.PathLike[str]) -> str:
    """从纯文本文件读取；路径无效、空文件或解码失败时返回 ``""``（不抛异常）。"""
    return read_contract_from_txt_outcome(file_path).get("text") or ""


def read_contract_from_txt_outcome(file_path: str | os.PathLike[str]) -> ContractReadOutcome:
    path = _as_path(file_path)
    if not path.is_file():
        return {"text": "", "error": f"文件不存在或不是文件：{path}"}
    try:
        if path.stat().st_size == 0:
            return {"text": "", "error": "文件为空（0 字节）"}
    except OSError as e:
        return {"text": "", "error": f"无法读取文件信息：{e}"}

    try:
        raw = path.read_bytes()
    except OSError as e:
        return {"text": "", "error": f"读取文件失败：{e}"}

    text: str
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    cleaned = _clean_extracted_text(text)
    if not cleaned.strip():
        return {"text": "", "error": "文本文件解码后无可见内容"}
    return {"text": cleaned, "error": None}


def read_contract_from_pdf(file_path: str | os.PathLike[str]) -> str:
    return read_contract_from_pdf_outcome(file_path).get("text") or ""


def read_contract_from_pdf_outcome(file_path: str | os.PathLike[str]) -> ContractReadOutcome:
    path = _as_path(file_path)
    if not path.is_file():
        return {"text": "", "error": f"文件不存在或不是文件：{path}"}
    try:
        if path.stat().st_size == 0:
            return {"text": "", "error": "文件为空（0 字节）"}
    except OSError as e:
        return {"text": "", "error": f"无法读取文件信息：{e}"}

    Reader, err = _resolve_pdf_reader()
    if Reader is None:
        msg = err or "PDF 库不可用"
        logger.warning("contract pdf: %s", msg)
        return {"text": "", "error": msg}

    try:
        reader = Reader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text()
            except Exception as e:  # noqa: BLE001 — 单页失败跳过
                logger.debug("contract pdf page extract failed: %s", e)
                continue
            if t and str(t).strip():
                parts.append(str(t))
        raw = "\n\n".join(parts)
        cleaned = _clean_extracted_text(raw)
        if not cleaned:
            return {
                "text": "",
                "error": "PDF 未提取到可见文本（可能为扫描件/图片版，需 OCR；或非文本 PDF）",
            }
        return {"text": cleaned, "error": None}
    except Exception as e:  # noqa: BLE001
        logger.exception("contract pdf read failed")
        return {"text": "", "error": f"PDF 读取失败：{e}"}


def read_contract_from_docx(file_path: str | os.PathLike[str]) -> str:
    return read_contract_from_docx_outcome(file_path).get("text") or ""


def read_contract_from_docx_outcome(file_path: str | os.PathLike[str]) -> ContractReadOutcome:
    path = _as_path(file_path)
    if not path.is_file():
        return {"text": "", "error": f"文件不存在或不是文件：{path}"}
    try:
        if path.stat().st_size == 0:
            return {"text": "", "error": "文件为空（0 字节）"}
    except OSError as e:
        return {"text": "", "error": f"无法读取文件信息：{e}"}

    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError:
        msg = "未安装 DOCX 库：请执行 pip install python-docx"
        logger.warning("contract docx: %s", msg)
        return {"text": "", "error": msg}

    try:
        doc = Document(str(path))
        lines: list[str] = []
        for p in doc.paragraphs:
            if p.text and p.text.strip():
                lines.append(p.text.strip())
        raw = "\n".join(lines)
        cleaned = _clean_extracted_text(raw)
        if not cleaned:
            return {"text": "", "error": "DOCX 中未提取到段落文本（可能仅含图片或空文档）"}
        return {"text": cleaned, "error": None}
    except Exception as e:  # noqa: BLE001
        logger.exception("contract docx read failed")
        return {"text": "", "error": f"DOCX 读取失败：{e}"}


def _infer_source_type_from_suffix(path: Path) -> ContractSourceType:
    suf = path.suffix.lower()
    if suf == ".pdf":
        return "pdf"
    if suf == ".docx":
        return "docx"
    if suf == ".txt":
        return "txt"
    return "txt"


def extract_contract_text_outcome(
    file_path: str | os.PathLike[str],
    source_type: str | None = None,
) -> ContractReadOutcome:
    """
    按路径与可选 ``source_type`` 提取文本；失败时 ``text`` 为空字符串，``error`` 说明原因。
    """
    path = _as_path(file_path)
    try:
        if source_type is None:
            st = _infer_source_type_from_suffix(path)
        else:
            st = coerce_contract_source_type(source_type)
            if st == "text":
                st = "txt"

        if st == "txt":
            return read_contract_from_txt_outcome(path)
        if st == "pdf":
            return read_contract_from_pdf_outcome(path)
        if st == "docx":
            return read_contract_from_docx_outcome(path)
        return read_contract_from_txt_outcome(path)
    except Exception as e:  # noqa: BLE001 — 保证不冒泡
        logger.exception("extract_contract_text_outcome failed")
        return {"text": "", "error": f"提取过程异常：{e}"}


def extract_contract_text(file_path: str | os.PathLike[str], source_type: str | None = None) -> str:
    """仅返回正文字符串；失败时为空字符串（不抛异常）。"""
    return extract_contract_text_outcome(file_path, source_type=source_type).get("text") or ""
