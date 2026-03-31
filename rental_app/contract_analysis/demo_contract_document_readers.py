"""
Phase 3 Part 4：固定样例 ``sample_contract.{txt,pdf,docx}`` — 文档读取 + 合同分析 + explain。

样例路径：``contract_analysis/samples/``。若缺少 ``.pdf`` / ``.docx``，在 ``rental_app`` 下执行::

    python scripts/generate_sample_contract_documents.py

运行本演示::

    python -m contract_analysis.demo_contract_document_readers
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .contract_document_reader import extract_contract_text_outcome
from .service import analyze_contract_file_with_explain


def _samples_dir() -> Path:
    return Path(__file__).resolve().parent / "samples"


def sample_contract_paths() -> tuple[Path, Path, Path]:
    """仓库内固定样例：``sample_contract.txt`` / ``.pdf`` / ``.docx``。"""
    d = _samples_dir()
    return (d / "sample_contract.txt", d / "sample_contract.pdf", d / "sample_contract.docx")


def _preview_line(s: str, n: int = 100) -> str:
    one = (s or "").strip().replace("\n", " ")
    if len(one) > n:
        return one[:n] + "..."
    return one


def run_contract_file_demo() -> None:
    """
    依次：读取 txt → pdf → docx（``extract_contract_text_outcome``），
    再 ``analyze_contract_file_with_explain``，打印 explain 核心字段。
    """
    print("=== run_contract_file_demo (sample_contract.*) ===\n")
    txt_p, pdf_p, docx_p = sample_contract_paths()

    for label, path in (
        ("TXT", txt_p),
        ("PDF", pdf_p),
        ("DOCX", docx_p),
    ):
        print(f"--- {label}: {path.name} ---")
        if not path.is_file():
            print(
                f"  [skip] 文件不存在: {path}\n"
                f"  若缺 pdf/docx 请运行: python scripts/generate_sample_contract_documents.py\n"
            )
            continue

        read_out = extract_contract_text_outcome(path)
        if read_out.get("error"):
            print(f"  [read] error: {read_out['error']}\n")
            continue
        body = read_out.get("text") or ""
        print(f"  [read] ok, chars={len(body)} preview: {_preview_line(body, 90)!r}")

        out = analyze_contract_file_with_explain(file_path=path)
        ex = out.get("explain") or {}
        sa = out.get("structured_analysis") or {}
        print(f"  [meta] {sa.get('meta')}")
        print(f"  [explain] overall_conclusion: {_preview_line(ex.get('overall_conclusion') or '', 200)}")
        print(f"  [explain] key_risk_summary: {_preview_line(ex.get('key_risk_summary') or '', 200)}")
        n_sum = len(ex.get("risk_category_summary") or [])
        n_grp = len(ex.get("risk_category_groups") or [])
        print(f"  [explain] risk_category_summary: {n_sum} row(s), risk_category_groups: {n_grp} group(s)")
        print()

    print("=== done ===")


def test_contract_document_readers() -> None:
    """
    断言 ``samples/sample_contract.*`` 存在且可读、分析管线完整（供脚本与 pytest 复用）。

    若缺少二进制样例，请先运行 ``python scripts/generate_sample_contract_documents.py``。
    """
    txt_p, pdf_p, docx_p = sample_contract_paths()
    for path in (txt_p, pdf_p, docx_p):
        assert path.is_file(), (
            f"缺少样例文件: {path} — 运行 python scripts/generate_sample_contract_documents.py"
        )
        ro = extract_contract_text_outcome(path)
        assert not ro.get("error"), f"读取失败 {path}: {ro.get('error')}"
        assert (ro.get("text") or "").strip(), f"正文为空: {path}"

        out = analyze_contract_file_with_explain(file_path=path)
        assert "structured_analysis" in out and "explain" in out
        ex = out["explain"]
        sa = out["structured_analysis"]
        for k in ("overall_conclusion", "key_risk_summary", "missing_clause_summary"):
            assert isinstance(ex.get(k), str) and (ex.get(k) or "").strip()
        assert isinstance(ex.get("risk_category_groups"), list)
        assert isinstance(ex.get("risk_category_summary"), list)
        assert isinstance(ex.get("clause_overview"), list)
        assert isinstance(ex.get("clause_risk_overview"), list)
        assert isinstance(ex.get("clause_severity_overview"), list)
        assert isinstance(sa.get("clause_list"), list)
        assert isinstance(sa.get("clause_risk_map"), list)
        assert isinstance(sa.get("clause_severity_summary"), list)
        assert isinstance(sa.get("risk_category_groups"), list)
        assert isinstance(sa.get("risk_category_summary"), list)
        assert len(ex["risk_category_groups"]) == len(ex["risk_category_summary"])
        adv = ex.get("action_advice")
        assert isinstance(adv, list) and len(adv) >= 3
        hrc = ex.get("highlighted_risk_clauses")
        assert isinstance(hrc, list)
        risks_n = len(sa.get("risks") or [])
        assert len(hrc) == min(risks_n, 20)
        for card in hrc:
            assert isinstance(card, dict)
            for key in ("risk_title", "severity", "short_advice"):
                assert key in card


if __name__ == "__main__":
    run_contract_file_demo()
