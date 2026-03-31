"""
Phase 3 合同分析：主分析入口（基础规则扫描 + 主题覆盖）。
"""

from __future__ import annotations

import re
from typing import Any, cast

from .contract_models import (
    ContractAnalysisResult,
    ContractInput,
    coerce_contract_clause_type,
    coerce_contract_risk_category,
    coerce_contract_source_type,
)

# 与 ``ContractRiskCategory`` 顺序一致，便于稳定排序（仅用于分组展示）
_RCS_CATEGORY_ORDER: tuple[str, ...] = (
    "deposit",
    "fees",
    "access",
    "repairs",
    "notice",
    "rent_increase",
    "termination",
    "bills",
    "pets",
    "subletting",
    "inventory",
    "general",
)
_RCS_CATEGORY_ORDER_INDEX = {c: i for i, c in enumerate(_RCS_CATEGORY_ORDER)}

_RCS_SUMMARY_LABEL_ZH: dict[str, str] = {
    "deposit": "押金与托管",
    "fees": "费用与收费",
    "access": "进入 / 查看权",
    "repairs": "维修责任",
    "notice": "通知期",
    "rent_increase": "涨租",
    "termination": "解约 / 终止",
    "bills": "账单与 utilities",
    "pets": "宠物政策",
    "subletting": "转租",
    "inventory": "房屋清单",
    "general": "其他 / 未归类",
}
from .contract_clause_split import parse_contract_clauses
from .contract_rules import (
    detect_contract_topic_labels,
    evaluate_deposit_amount_risk,
    match_clause_type_from_text,
    scan_text_keyword_risks,
    scan_topic_bad_pattern_risks,
    scan_topic_missing_items,
)


def _dedupe_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in risks:
        rid = str(r.get("rule_id") or r.get("title") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    return out


def _meta_from_input(contract_input: ContractInput) -> dict[str, Any]:
    """与 ``ContractInput`` 对齐的回显元数据（供 API / 前端展示来源）。"""
    st = coerce_contract_source_type(contract_input.source_type)
    return {"source_type": st, "source_name": contract_input.source_name}


def _sort_category_key(category: str) -> tuple[int, str]:
    return (_RCS_CATEGORY_ORDER_INDEX.get(category, 10_000), category)


def _severity_rank_label(severity: str) -> tuple[int, str]:
    s = str(severity or "medium").strip().lower()
    rank = {"high": 2, "medium": 1, "low": 0}.get(s, 1)
    label = s if s in ("high", "medium", "low") else "medium"
    return rank, label


def _highest_severity_in_risks(risks: list[dict[str, Any]]) -> str:
    best_r, best_l = -1, "low"
    for r in risks:
        if not isinstance(r, dict):
            continue
        rr, lab = _severity_rank_label(str(r.get("severity") or ""))
        if rr > best_r:
            best_r, best_l = rr, lab
    return best_l


def group_risks_by_category(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    将已归一化的 ``risks`` 按 ``risk_category`` 分组；组内顺序与输入中首次出现顺序一致。
    返回 ``[{ \"category\": str, \"risks\": list[dict] }, ...]``（稳定空列表当无风险）。
    """
    if not risks:
        return []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in risks:
        if not isinstance(r, dict):
            continue
        cat = coerce_contract_risk_category(r.get("risk_category"))
        buckets.setdefault(cat, []).append(r)
    ordered = sorted(buckets.keys(), key=_sort_category_key)
    return [{"category": c, "risks": buckets[c]} for c in ordered]


def build_risk_category_summary(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    按类汇总：条数、最高严重度、短文案（中文）。
    与 ``group_risks_by_category`` 的分类顺序一致。
    """
    groups = group_risks_by_category(risks)
    out: list[dict[str, Any]] = []
    for g in groups:
        cat = str(g.get("category") or "general")
        rs = g.get("risks") if isinstance(g.get("risks"), list) else []
        rs = [x for x in rs if isinstance(x, dict)]
        n = len(rs)
        hi = _highest_severity_in_risks(rs)
        sev_zh = {"high": "高", "medium": "中", "low": "低"}.get(hi, hi)
        label = _RCS_SUMMARY_LABEL_ZH.get(cat, cat)
        short_summary = f"{label}：共 {n} 条提示，本类最高严重度为「{sev_zh}」。"
        out.append(
            {
                "category": cat,
                "count": n,
                "highest_severity": hi,
                "short_summary": short_summary,
            }
        )
    return out


def _normalize_risk_dict(r: dict[str, Any]) -> dict[str, Any]:
    """每条 risk 含稳定字符串字段；无定位信息时安全降级为空串。"""
    rd = dict(r)
    for key, default in (
        ("matched_text", ""),
        ("matched_keyword", ""),
        ("location_hint", ""),
    ):
        v = rd.get(key)
        rd[key] = str(v).strip() if v is not None else default
    rc = rd.get("risk_category")
    rd["risk_category"] = coerce_contract_risk_category(str(rc).strip() if rc is not None else None)
    rcode = rd.get("risk_code")
    if rcode is None or not str(rcode).strip():
        rd["risk_code"] = str(rd.get("rule_id") or "general").strip() or "general"
    else:
        rd["risk_code"] = str(rcode).strip()
    return rd


def _normalize_clause_dict(c: dict[str, Any]) -> dict[str, Any]:
    """条款级占位结构归一化（Part 7）；未知 ``clause_type`` 回退为 general。"""
    d = dict(c)
    d["clause_id"] = str(d.get("clause_id") or "").strip()
    d["clause_text"] = str(d.get("clause_text") or "").strip()
    ct = d.get("clause_type")
    d["clause_type"] = coerce_contract_clause_type(str(ct).strip() if ct is not None else None)
    mk = d.get("matched_keywords")
    if not isinstance(mk, list):
        mk = []
    d["matched_keywords"] = [str(x).strip() for x in mk if str(x).strip()]
    rf = d.get("risk_flags")
    if not isinstance(rf, list):
        rf = []
    d["risk_flags"] = [str(x).strip() for x in rf if str(x).strip()]
    d["location_hint"] = str(d.get("location_hint") or "").strip()
    return d


_RE_LOC_SENTENCE = re.compile(r"matched sentence\s+(\d+)", re.IGNORECASE)
_RE_CLAUSE_ID_NUM = re.compile(r"^clause_(\d+)$", re.IGNORECASE)


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _clause_index_from_id(clause_id: str) -> int | None:
    m = _RE_CLAUSE_ID_NUM.match((clause_id or "").strip())
    return int(m.group(1)) if m else None


def _sentence_index_from_location_hint(location_hint: str) -> int | None:
    m = _RE_LOC_SENTENCE.search(location_hint or "")
    return int(m.group(1)) if m else None


def _matched_text_overlaps_clause(clause_text: str, matched_text: str) -> bool:
    """matched_text 与条款正文有明显重叠：整段包含，或取较短段的前缀子串包含。"""
    ct = _normalize_ws(clause_text).lower()
    mt = _normalize_ws(matched_text).lower()
    if not mt or len(mt) < 3:
        return False
    if mt in ct:
        return True
    # 长窗口：取前 120 字符再试（避免切分导致整行未完全落入单条 clause）
    chunk = mt[:120] if len(mt) > 120 else mt
    return len(chunk) >= 8 and chunk in ct


def _matched_keyword_in_clause(clause_text: str, matched_keyword: str) -> bool:
    kw = (matched_keyword or "").strip()
    if len(kw) < 2:
        return False
    return kw.lower() in _normalize_ws(clause_text).lower()


def _location_hint_aligns_clause(location_hint: str, clause_id: str) -> bool:
    """location_hint 中出现 clause_id，或「matched sentence N」与 clause_N 序号一致。"""
    lh = (location_hint or "").strip()
    cid = (clause_id or "").strip()
    if not lh or not cid:
        return False
    if cid.lower() in lh.lower():
        return True
    si = _sentence_index_from_location_hint(lh)
    ci = _clause_index_from_id(cid)
    if si is not None and ci is not None and si == ci:
        return True
    return False


def _numeric_deposit_risk_to_deposit_clause(
    rule_id: str,
    matched_text: str,
    matched_keyword: str,
    location_hint: str,
    clause_text: str,
) -> bool:
    """
    ``deposit_amount_high`` 仅有用户填写数值、无 ``matched_text`` 时，挂到含 deposit/押金 的条款上。
    """
    if rule_id != "deposit_amount_high":
        return False
    if (matched_text or "").strip() or (matched_keyword or "").strip():
        return False
    lh = (location_hint or "").strip()
    if "用户填写" not in lh and "非合同正文" not in lh:
        return False
    low = (clause_text or "").lower()
    return "deposit" in low or "押金" in (clause_text or "")


def build_clause_risk_map(
    clause_list: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    将 ``risks`` 与 ``clause_list`` 做轻量联动（无 NLP）。

    对每条 risk，按条款顺序找**第一条**满足以下任一条件的条款并生成一条记录（否则跳过该 risk）：

    1. ``matched_text`` 与 ``clause_text`` 有明显子串重叠；
    2. ``matched_keyword`` 出现在 ``clause_text`` 中；
    3. ``location_hint`` 与 ``clause_id`` 可粗略对应（含 clause_id 子串，或 sentence 序号与 clause 序号一致）。

    每项含 ``ClauseRiskLinkItem`` 字段；``link_reason`` 为固定英文短语便于前端与日志。
    """
    clauses = [c for c in clause_list if isinstance(c, dict)]
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for r in risks:
        if not isinstance(r, dict):
            continue
        rule_id = str(r.get("rule_id") or "").strip()
        if not rule_id:
            continue
        mt = str(r.get("matched_text") or "").strip()
        mk = str(r.get("matched_keyword") or "").strip()
        lh = str(r.get("location_hint") or "").strip()
        title = str(r.get("title") or rule_id).strip()
        sev = str(r.get("severity") or "medium").strip().lower()
        if sev not in ("high", "medium", "low"):
            sev = "medium"
        rc = coerce_contract_risk_category(r.get("risk_category"))

        for c in clauses:
            cid = str(c.get("clause_id") or "").strip()
            ctext = str(c.get("clause_text") or "")
            if not cid or not ctext:
                continue

            link_reason = ""
            if _matched_text_overlaps_clause(ctext, mt):
                link_reason = "matched text overlaps with clause"
            elif _matched_keyword_in_clause(ctext, mk):
                link_reason = "matched keyword found in clause text"
            elif _location_hint_aligns_clause(lh, cid):
                link_reason = "location_hint aligns with clause id"
            elif _numeric_deposit_risk_to_deposit_clause(rule_id, mt, mk, lh, ctext):
                link_reason = "numeric deposit risk matched to deposit-related clause"
            else:
                continue

            key = (cid, rule_id)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "clause_id": cid,
                    "risk_title": title,
                    "risk_category": rc,
                    "severity": sev,
                    "matched_keyword": mk,
                    "matched_text": mt,
                    "location_hint": lh,
                    "link_reason": link_reason,
                }
            )
            break

    return out


def _normalize_clause_risk_link_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Part 8：条款—风险联动行归一化；``severity`` 非标准值时回退为 medium。"""
    x = dict(d)
    for key, default in (
        ("clause_id", ""),
        ("risk_title", ""),
        ("matched_keyword", ""),
        ("matched_text", ""),
        ("location_hint", ""),
        ("link_reason", ""),
    ):
        v = x.get(key)
        x[key] = str(v).strip() if v is not None else default
    rc = x.get("risk_category")
    x["risk_category"] = coerce_contract_risk_category(str(rc).strip() if rc is not None else None)
    sev = str(x.get("severity") or "").strip().lower()
    x["severity"] = sev if sev in ("high", "medium", "low") else "medium"
    return x


def _normalize_analysis_output(data: dict[str, Any]) -> dict[str, Any]:
    """保证输出字段类型稳定：risks / clause_list / clause_risk_map / missing_items 等均为 list。"""
    out = dict(data)
    raw_risks = out.get("risks")
    if not isinstance(raw_risks, list):
        raw_risks = []
    out["risks"] = [_normalize_risk_dict(x) for x in raw_risks if isinstance(x, dict)]
    raw_clauses = out.get("clause_list")
    if not isinstance(raw_clauses, list):
        raw_clauses = []
    out["clause_list"] = [_normalize_clause_dict(x) for x in raw_clauses if isinstance(x, dict)]
    raw_links = out.get("clause_risk_map")
    if not isinstance(raw_links, list):
        raw_links = []
    out["clause_risk_map"] = [_normalize_clause_risk_link_dict(x) for x in raw_links if isinstance(x, dict)]
    for key in ("missing_items", "recommendations", "detected_topics"):
        v = out.get(key)
        if not isinstance(v, list):
            v = []
        else:
            v = [str(i).strip() for i in v if str(i).strip()]
        out[key] = v
    out["summary"] = str(out.get("summary") or "").strip()
    out["risk_category_groups"] = group_risks_by_category(out["risks"])
    out["risk_category_summary"] = build_risk_category_summary(out["risks"])
    return out


def _missing_covers_notice_and_repair(missing_items: list[str]) -> bool:
    """用于针对性建议：同时缺失通知期与维修主题。"""
    has_n = any(("Notice" in m or "通知期" in m) for m in missing_items)
    has_r = any(("Repair" in m or "Maintenance" in m or "维修" in m) for m in missing_items)
    return has_n and has_r


def _uniq_preserve(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        t = (x or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def detect_clause_type(clause_text: str) -> tuple[str, list[str]]:
    """
    对单条条款文本识别 ``clause_type`` 与命中的关键词（见 ``contract_rules.CLAUSE_TYPE_KEYWORDS``）。

    返回 ``(clause_type, matched_keywords)``；与 ``match_clause_type_from_text`` 一致。
    """
    return match_clause_type_from_text(clause_text)


def annotate_clause_types(clause_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    为 ``parse_contract_clauses`` 产出的条目写入 ``clause_type`` / ``matched_keywords``（就地更新）。
    多主题时仅保留优先级最高的一类（见 ``CLAUSE_TYPE_DETECTION_ORDER``）。
    """
    for item in clause_list:
        if not isinstance(item, dict):
            continue
        text = str(item.get("clause_text") or "")
        ct, kws = match_clause_type_from_text(text)
        item["clause_type"] = ct
        item["matched_keywords"] = kws
    return clause_list


def detect_contract_topics(contract_text: str) -> list[str]:
    """返回合同中已识别到的主题标签列表（人类可读）。"""
    return detect_contract_topic_labels(contract_text)


def detect_contract_risks(contract_text: str, contract_input: ContractInput) -> list[dict[str, Any]]:
    """合并：数值押金风险 + Part1 全局关键词 + Part2 主题不合理表述。"""
    risks: list[dict[str, Any]] = []
    dep = evaluate_deposit_amount_risk(contract_input.deposit_amount, contract_input.monthly_rent)
    if dep is not None:
        risks.append(dep)
    risks.extend(scan_text_keyword_risks(contract_text))
    risks.extend(scan_topic_bad_pattern_risks(contract_text))
    return _dedupe_risks(risks)


def detect_missing_items(contract_text: str) -> list[str]:
    """未覆盖的主题列表（文案标签）。"""
    return scan_topic_missing_items(contract_text)


def build_contract_summary(
    risks: list[dict[str, Any]],
    missing_items: list[str],
    detected_topics: list[str],
) -> str:
    """生成摘要句，便于 UI / explain 展示。"""
    rc, mc, dc = len(risks), len(missing_items), len(detected_topics)
    if rc == 0 and mc == 0:
        return (
            f"已识别 {dc} 个常见主题关键词；未发现全局规则命中的风险项或明显主题缺失。"
            "仍请通读全文并自行核对事实与数字。"
        )
    parts = [
        f"共提示 {rc} 条风险项",
        f"正文约覆盖 {dc} 类常见主题",
        f"另有 {mc} 类主题未在文中匹配到关键词（可能未约定或写在附件）",
    ]
    return "；".join(parts) + "。"


def build_recommendations(
    risks: list[dict[str, Any]],
    missing_items: list[str],
    detected_topics: list[str],
) -> list[str]:
    """根据命中规则与缺失项生成简短建议（中文）。"""
    recs: list[str] = []
    rule_ids = {str(r.get("rule_id") or "") for r in risks}

    if "deposit_amount_high" in rule_ids:
        recs.append(
            "请核对押金是否已按当地要求存入政府认可的托管计划（如 DPS、TDS、MyDeposits），并保存证书。"
        )

    fee_ids = {"fee_suspicious_generic", "fee_penalty", "fee_non_refundable", "fee_admin_cleaning"}
    if rule_ids & fee_ids:
        recs.append("逐项核对费用名称与金额；避免将本不应单独收取的项目与押金或首月租金混同。")

    if (
        "landlord_enter_anytime" in rule_ids
        or "no_notice_termination" in rule_ids
        or "access_no_notice_bad" in rule_ids
    ):
        recs.append("对进入权、通知期与解约程序有疑问时，建议对照当地现行租赁法规或咨询 Citizens Advice 类渠道。")

    if "landlord_enter_anytime" in rule_ids or "access_no_notice_bad" in rule_ids:
        recs.append("进入权条款应写明合理通知时间与紧急情况例外；若与口头承诺不一致，以书面条款为准。")

    if "tenant_all_repairs" in rule_ids:
        recs.append("结构性维修与房东法定义务通常不可通过合同全部转嫁给租客；建议请专业人士审阅维修条款范围。")

    if "rent_increase_unfair" in rule_ids:
        recs.append("涨租条款若过于宽泛，可要求出租方明确程序、频率与通知期。")

    if "deposit_not_protected_text" in rule_ids:
        recs.append("若合同暗示押金未托管，签约前应要求书面澄清托管方案与证书。")

    if _missing_covers_notice_and_repair(missing_items):
        recs.append("正文若未同时写明通知期与维修责任，建议索取标准条款或让房东确认补充后再签署。")

    if len(missing_items) >= 6:
        recs.append("缺失主题较多时，可要求对方提供标准条款附录或修订后再签署。")
    elif missing_items:
        recs.append("对合同中未明确写清的主题，可要求出租方在签约前以书面补充条款或附录说明。")

    if not detected_topics:
        recs.append("若正文极短或未包含常见条款关键词，建议换用完整合同 PDF/全文再分析。")

    recs.append("本分析基于关键词与简单规则，不构成法律意见；签约前请通读全文并保留沟通记录。")

    return _uniq_preserve(recs)


def analyze_contract_text(contract_input: ContractInput) -> ContractAnalysisResult:
    """
    对合同文本做基础规则分析。

    返回字段与 ``ContractAnalysisResult`` 一致：
    - summary, risks, risk_category_groups, risk_category_summary,
      clause_list（``parse_contract_clauses`` + ``annotate_clause_types``）
    - clause_risk_map：条款—风险联动列表（由 ``build_clause_risk_map`` 生成；见 ``ClauseRiskLinkItem``）
    - missing_items, recommendations, detected_topics
    - meta: { source_type, source_name }（与 ``ContractInput`` 对应）
    """
    text = (contract_input.contract_text or "").strip()
    if not text:
        out = _normalize_analysis_output(
            {
                "summary": "未提供合同文本，无法分析。",
                "risks": [],
                "missing_items": ["合同正文"],
                "recommendations": ["请上传或粘贴完整合同文本后再试。"],
                "detected_topics": [],
            }
        )
        out["meta"] = _meta_from_input(contract_input)
        return out  # type: ignore[return-value]

    detected_topics = detect_contract_topics(text)
    risks = detect_contract_risks(text, contract_input)
    missing_items = detect_missing_items(text)
    recommendations = build_recommendations(risks, missing_items, detected_topics)
    summary = build_contract_summary(risks, missing_items, detected_topics)
    clause_list = parse_contract_clauses(text)
    clause_list = annotate_clause_types(clause_list)
    clause_risk_map = build_clause_risk_map(clause_list, risks)

    out = _normalize_analysis_output(
        {
            "summary": summary,
            "risks": risks,
            "clause_list": clause_list,
            "clause_risk_map": clause_risk_map,
            "missing_items": missing_items,
            "recommendations": recommendations,
            "detected_topics": detected_topics,
        }
    )
    out["meta"] = _meta_from_input(contract_input)
    return cast(ContractAnalysisResult, out)
