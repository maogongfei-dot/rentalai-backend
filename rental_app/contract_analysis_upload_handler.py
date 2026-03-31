"""
Phase 4：multipart 合同上传 → 临时文件 → ``contract_analysis_service.analyze_contract_file``。

与 ``api_server`` 路由解耦：仅负责校验、落盘、调用门面、清理临时文件。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import UploadFile

from contract_analysis_service import ContractAnalysisFacadeResult, analyze_contract_file

ALLOWED_SUFFIXES = frozenset({".txt", ".pdf", ".docx"})


class ContractUploadError(Exception):
    """上传前置校验失败（客户端可修正）。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def contract_upload_max_bytes() -> int:
    return max(1, int(os.environ.get("RENTALAI_CONTRACT_UPLOAD_MAX_BYTES", str(15 * 1024 * 1024))))


def _suffix(name: str) -> str:
    return Path(name or "").suffix.lower()


async def analyze_contract_from_upload(
    upload: UploadFile,
    *,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str | None = None,
    source_name: str | None = None,
) -> ContractAnalysisFacadeResult:
    """
    读取 ``UploadFile``，写入临时路径后调用 ``analyze_contract_file``（与路径接口同一引擎）。

    - 允许类型：``.txt`` / ``.pdf`` / ``.docx``
    - ``source_name``：写入 ``meta``；默认用上传原始文件名
    - ``source_type``：通常由扩展名推断；若调用方传入（如 metadata）则覆盖

    前置错误抛出 :class:`ContractUploadError`；抽取/分析失败抛出 ``ValueError``（与读盘路径一致）。
    """
    fn = (upload.filename or "").strip()
    if not fn:
        raise ContractUploadError("empty_filename", "缺少文件名，请重新选择文件。")

    suf = _suffix(fn)
    if suf not in ALLOWED_SUFFIXES:
        raise ContractUploadError(
            "unsupported_file_type",
            f"不支持的文件类型：仅支持 .txt、.pdf、.docx；当前为 {suf or '（无扩展名）'}。",
        )

    try:
        raw = await upload.read()
    except Exception as exc:
        raise ContractUploadError(
            "read_failed",
            f"读取上传文件失败：{exc}",
        ) from exc

    if not raw:
        raise ContractUploadError("empty_file", "上传的文件为空（0 字节），请选择有效合同文件。")

    max_b = contract_upload_max_bytes()
    if len(raw) > max_b:
        mb = max_b / (1024 * 1024)
        raise ContractUploadError(
            "file_too_large",
            f"文件过大：单文件上限约 {mb:.0f} MB（{max_b} 字节），请压缩或拆分后再试。",
        )

    inferred = suf.lstrip(".")  # txt | pdf | docx
    exp = (str(source_type).strip().lower() if source_type is not None else "")
    st = exp if exp in ("txt", "pdf", "docx") else inferred
    display = (source_name or fn).strip() or fn

    tmp_path: Path | None = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(suffix=suf, prefix="rentalai_contract_")
        os.close(fd)
        tmp_path = Path(tmp_path_str)
        tmp_path.write_bytes(raw)
        return analyze_contract_file(
            file_path=tmp_path,
            monthly_rent=monthly_rent,
            deposit_amount=deposit_amount,
            fixed_term_months=fixed_term_months,
            source_type=st,
            source_name=display,
        )
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
