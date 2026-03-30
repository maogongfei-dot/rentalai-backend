#!/usr/bin/env python3
"""
Phase 3 合同分析 CLI：默认输出「产品化」分段报告；``--json`` 输出完整结构化 JSON。

用法（在 rental_app 目录下）::

    python scripts/contract_phase3_demo.py path/to/contract.txt
    python scripts/contract_phase3_demo.py path/to/contract.pdf
    python scripts/contract_phase3_demo.py --json path/to/contract.docx
    echo "Rent 800 pcm. Admin fee 200." | python scripts/contract_phase3_demo.py

支持 ``.txt`` / ``.pdf`` / ``.docx``：走 ``analyze_contract_file_with_explain``；
从 stdin 读取时仍为纯文本 ``analyze_contract_with_explain``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_stdin_text() -> str:
    return sys.stdin.read()


def _is_doc_path(path: Path) -> bool:
    return path.suffix.lower() in (".txt", ".pdf", ".docx")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 合同分析 CLI（两层输出 + 展示层）")
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="合同文件路径（.txt / .pdf / .docx）或任意文本文件；省略则从 stdin 读取",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出完整 JSON（structured_analysis / explain / presentation）",
    )
    args = parser.parse_args()

    root = _root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from contract_analysis.service import (
        analyze_contract_file_with_explain,
        analyze_contract_with_explain,
    )

    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        if _is_doc_path(path):
            out = analyze_contract_file_with_explain(file_path=path)
        else:
            # 其它扩展名：按 UTF-8 文本读入（与旧行为兼容）
            text = path.read_text(encoding="utf-8", errors="replace")
            out = analyze_contract_with_explain(
                contract_text=text,
                source_type="txt",
                source_name=path.name,
            )
    else:
        text = _load_stdin_text()
        out = analyze_contract_with_explain(contract_text=text)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return

    pres = out.get("presentation") or {}
    plain = pres.get("plain_text")
    if isinstance(plain, str) and plain.strip():
        print(plain)
        return

    from contract_analysis.presentation import format_contract_analysis_cli_report

    sa = out.get("structured_analysis") or {}
    ex = out.get("explain") or {}
    print(format_contract_analysis_cli_report(sa, ex))


if __name__ == "__main__":
    main()
