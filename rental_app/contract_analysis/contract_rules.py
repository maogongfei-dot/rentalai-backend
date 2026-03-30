"""
Phase 3 合同分析：英国租房合同基础风险检查（关键词 / 简单文本规则，无 NLP 依赖）。

Part 2：按主题覆盖（detected_topics / missing_items）与主题级不合理表述（risks）。
说明：非法律意见；押金数值规则见 evaluate_deposit_amount_risk。
"""

from __future__ import annotations

import re
from typing import Any

# --- 严重级别（与项目其它模块常见取值对齐）---
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# 五周租金折算为「月租」倍数：5 * (12/52) ≈ 1.1538
_UK_FIVE_WEEKS_OF_MONTHLY_RENT = 60.0 / 52.0

# ---------------------------------------------------------------------------
# Part 1：全局文本关键词风险（BASIC_CONTRACT_RISK_RULES，保持兼容）
# ---------------------------------------------------------------------------

BASIC_CONTRACT_RISK_RULES: list[dict[str, Any]] = [
    {
        "id": "fee_suspicious_generic",
        "patterns": [
            r"\bsuspicious\s+fee\b",
            r"\bhidden\s+fee\b",
            r"\bunreasonable\s+fee\b",
            r"\bundisclosed\s+charges?\b",
            r"\bundisclosed\s+fees?\b",
            r"\bmandatory\s+fees?\b",
        ],
        "title": "疑似不合理或模糊收费表述",
        "severity": SEVERITY_MEDIUM,
        "reason": "合同中出现与「可疑费用、隐藏收费」等相关的英文表述，建议逐项核对费用明细与合法性。",
    },
    {
        "id": "fee_penalty",
        "patterns": [
            r"\bpenalty\b",
            r"\bpenalties\b",
            r"\blate\s+payment\s+fee\b",
            r"\bdefault\s+fee\b",
        ],
        "title": "违约金 / 滞纳金类条款",
        "severity": SEVERITY_MEDIUM,
        "reason": "出现 penalty、滞纳金等关键词，请确认金额上限、触发条件是否符合公平原则。",
    },
    {
        "id": "fee_non_refundable",
        "patterns": [
            r"\bnon[- ]?refundable\b",
            r"\bnon[- ]?returnable\b",
            r"不予退还",
            r"不退还",
        ],
        "title": "不可退款收费",
        "severity": SEVERITY_HIGH,
        "reason": "出现「不可退款」类表述，需确认对应项目是否为法定允许范围（如部分行政费已受限）。",
    },
    {
        "id": "fee_admin_cleaning",
        "patterns": [
            r"\badmin(istrative)?\s+fee\b",
            r"\bcleaning\s+fee\b",
            r"\bcheck[- ]?in\s+fee\b",
            r"\bcheck[- ]?out\s+fee\b",
            r"\bholding\s+deposit\b",
        ],
        "title": "行政费 / 清洁费等附加收费",
        "severity": SEVERITY_MEDIUM,
        "reason": "出现行政费、清洁费等关键词；英格兰对租户可收费用种类有限制，请核对是否重复或与押金混同。",
    },
    {
        "id": "landlord_enter_anytime",
        "patterns": [
            r"enter\s+(at\s+)?any\s*time",
            r"access\s+without\s+notice",
            r"without\s+prior\s+notice",
            r"landlord\s+may\s+enter",
            r"随时进入",
            r"无需事先通知",
        ],
        "title": "房东进入房屋的通知义务存疑",
        "severity": SEVERITY_HIGH,
        "reason": "条款可能削弱租客对安宁占有的合理预期；合法进入通常需合理通知（紧急情况除外）。",
    },
    {
        "id": "tenant_all_repairs",
        "patterns": [
            r"tenant\s+(shall|must|will)\s+pay\s+(for\s+)?all\s+repairs",
            r"tenant\s+responsible\s+for\s+all\s+repairs",
            r"all\s+repairs\s+.*\s+tenant",
            r"租客承担.*全部维修",
            r"tenant\s+pays\s+all\s+maintenance",
        ],
        "title": "维修责任可能全部推给租客",
        "severity": SEVERITY_HIGH,
        "reason": "结构性维修与房东义务在英国通常不可通过合同全部转嫁给租客；需核对具体措辞与范围。",
    },
    {
        "id": "no_notice_termination",
        "patterns": [
            r"no\s+notice\s+required",
            r"\bwithout\s+notice\s+to\s+terminate\b",
            r"immediate\s+termination",
            r"无需通知.*终止",
        ],
        "title": "通知期 / 解除条件对租客不利",
        "severity": SEVERITY_MEDIUM,
        "reason": "出现「无需通知即可终止」等表述，请核对是否违反最低通知期与程序要求。",
    },
]

# ---------------------------------------------------------------------------
# Part 2：主题检查（覆盖关键词 + 可选「不合理」子规则）
# detected_topics：命中任一 coverage 关键词即视为该主题「有提及」
# missing_items：某主题完全未命中 coverage
# risks：命中 bad_patterns 中任一正则
# ---------------------------------------------------------------------------

CONTRACT_CHECK_TOPICS: list[dict[str, Any]] = [
    {
        "topic_id": "deposit_protection",
        "display_name": "押金托管（Deposit protection scheme）",
        "missing_label": "未提及押金托管/保护计划（Deposit protection）",
        "coverage_keywords": [
            "deposit protection",
            "protection scheme",
            "custodial scheme",
            "insured scheme",
            "mydeposits",
            "my deposits",
            "tds",
            "dps",
            "tenancy deposit scheme",
            "押金保护",
            "托管",
        ],
        "bad_rules": [
            {
                "id": "deposit_not_protected_text",
                "patterns": [
                    r"deposit\s+will\s+not\s+be\s+protected",
                    r"not\s+protected\s+by\s+a\s+scheme",
                    r"not\s+placed\s+in\s+a\s+(custodial|insured)\s+scheme",
                    r"无需托管",
                    r"押金不予托管",
                ],
                "title": "文本暗示押金可能未纳入保护计划",
                "severity": SEVERITY_HIGH,
                "reason": "若押金依法须托管，应明确计划名称与条款；请核对与房东/中介书面承诺是否一致。",
            },
        ],
    },
    {
        "topic_id": "rent_payment",
        "display_name": "租金与支付（Rent / Payment）",
        "missing_label": "未明确租金金额或支付方式（Rent payment）",
        "coverage_keywords": [
            "rent",
            "monthly",
            "per month",
            "pcm",
            "payable",
            "rental payment",
            "租金",
            "月租",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "notice_period",
        "display_name": "通知期（Notice period）",
        "missing_label": "未提及通知期或提前通知要求（Notice period）",
        "coverage_keywords": [
            "notice period",
            "period of notice",
            "notice required",
            "one month notice",
            "one month's notice",
            "two months notice",
            "months' notice",
            "months notice",
            "statutory notice",
            "通知期",
            "提前通知",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "rent_increase",
        "display_name": "涨租条款（Rent increase）",
        "missing_label": "未提及涨租或租金复查（Rent increase）",
        "coverage_keywords": [
            "rent increase",
            "increase in rent",
            "rent review",
            "review of rent",
            "annual increase",
            "涨租",
            "租金上调",
        ],
        "bad_rules": [
            {
                "id": "rent_increase_unfair",
                "patterns": [
                    r"rent\s+may\s+be\s+increased\s+at\s+any\s+time",
                    r"unlimited\s+rent\s+increase",
                    r"landlord\s+may\s+increase\s+rent\s+without\s+(notice|prior)",
                ],
                "title": "涨租表述可能过于宽泛",
                "severity": SEVERITY_HIGH,
                "reason": "出现「随时涨租、无限涨租」等措辞时需特别警惕，应核对法定程序与最低通知要求。",
            },
        ],
    },
    {
        "topic_id": "inventory_check",
        "display_name": "房屋清单与进退房（Inventory / Check-in / Check-out）",
        "missing_label": "未提及房屋清单或 check-in / check-out（Inventory）",
        "coverage_keywords": [
            "inventory",
            "check-in",
            "check in",
            "check-out",
            "check out",
            "schedule of condition",
            "ingoing",
            "outgoing",
            "房屋清单",
            "交接",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "break_clause",
        "display_name": "中断条款（Break clause）",
        "missing_label": "未提及中断条款（Break clause）",
        "coverage_keywords": [
            "break clause",
            "break option",
            "tenant's break",
            "break date",
            "中断",
            "提前解约权",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "early_termination",
        "display_name": "提前终止（Early termination）",
        "missing_label": "未提及提前终止/交回（Early termination）",
        "coverage_keywords": [
            "early termination",
            "early end",
            "surrender",
            "surrender of tenancy",
            "terminate early",
            "提前终止",
            "提前退租",
        ],
        "bad_rules": [
            {
                "id": "early_termination_harsh",
                "patterns": [
                    r"early\s+termination\s+fee\s+.*\s+non[- ]?refundable",
                    r"forfeit\s+.*\s+deposit.*\s+early",
                ],
                "title": "提前退租与费用/押金表述需核对",
                "severity": SEVERITY_MEDIUM,
                "reason": "若提前终止涉及高额费用或没收押金，请核对是否公平及是否与书面约定一致。",
            },
        ],
    },
    {
        "topic_id": "subletting",
        "display_name": "转租与转让（Subletting / Assignment）",
        "missing_label": "未提及转租、分租或转让（Subletting）",
        "coverage_keywords": [
            "sublet",
            "subletting",
            "sub-let",
            "assignment",
            "part with possession",
            "lodger",
            "转租",
            "分租",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "pets",
        "display_name": "宠物（Pets）",
        "missing_label": "未提及宠物政策（Pets）",
        "coverage_keywords": [
            "pets",
            "pet",
            "animals",
            "keeping animals",
            "no pets",
            "宠物",
        ],
        "bad_rules": [
            {
                "id": "pet_fee_harsh",
                "patterns": [
                    r"pet\s+fee\s+.*\s+non[- ]?refundable",
                    r"non[- ]?refundable\s+pet",
                ],
                "title": "宠物相关不可退款费用",
                "severity": SEVERITY_MEDIUM,
                "reason": "出现宠物不可退款费用时，请核对金额是否合理及是否与广告/沟通一致。",
            },
        ],
    },
    {
        "topic_id": "council_tax",
        "display_name": "市政税（Council tax）",
        "missing_label": "未提及市政税承担（Council tax）",
        "coverage_keywords": [
            "council tax",
            "local authority tax",
            "council tax band",
            "市政税",
            "地方税",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "utilities_bills",
        "display_name": "水电煤与账单（Utilities / Bills included）",
        "missing_label": "未明确水电燃气或是否包 bill（Utilities / Bills）",
        "coverage_keywords": [
            "utilities",
            "utility bills",
            "bills included",
            "bills excluded",
            "bills are",
            "gas",
            "electricity",
            "water charges",
            "水电",
            "包bill",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "maintenance_repairs",
        "display_name": "维修与维护（Maintenance / Repairs）",
        "missing_label": "未提及维修或维护责任（Maintenance / Repairs）",
        "coverage_keywords": [
            "maintenance",
            "repairs",
            "repairing",
            "landlord's repairing",
            "keep in repair",
            "维修",
            "维护",
        ],
        "bad_rules": [],
    },
    {
        "topic_id": "access_entry",
        "display_name": "进入与查看（Access / Entry notice）",
        "missing_label": "未提及房东/代理人进入房屋的条件（Access / Entry）",
        "coverage_keywords": [
            "access",
            "right of entry",
            "entry",
            "notice to enter",
            "inspect",
            "viewing",
            "reasonable notice",
            "进入",
            "查看房屋",
        ],
        "bad_rules": [
            {
                "id": "access_no_notice_bad",
                "patterns": [
                    r"landlord\s+may\s+enter\s+without\s+notice",
                    r"enter\s+at\s+any\s+time\s+without",
                ],
                "title": "进入权条款可能对租客不利",
                "severity": SEVERITY_HIGH,
                "reason": "除紧急情况外，进入通常应给予合理通知；请与 BASIC 规则命中结果一并核对。",
            },
        ],
    },
]


def _compile_rule_patterns(rule: dict[str, Any]) -> list[re.Pattern[str]]:
    out: list[re.Pattern[str]] = []
    for p in rule.get("patterns") or []:
        if not isinstance(p, str) or not p.strip():
            continue
        try:
            out.append(re.compile(p, re.IGNORECASE | re.MULTILINE))
        except re.error:
            continue
    return out


_COMPILED_BASIC_RULES: list[tuple[dict[str, Any], list[re.Pattern[str]]]] = [
    (r, _compile_rule_patterns(r)) for r in BASIC_CONTRACT_RISK_RULES
]

# 主题级 bad 规则预编译
_COMPILED_TOPIC_BAD: list[tuple[dict[str, Any], list[re.Pattern[str]]]] = []
for _topic in CONTRACT_CHECK_TOPICS:
    for br in _topic.get("bad_rules") or []:
        if not isinstance(br, dict):
            continue
        _COMPILED_TOPIC_BAD.append((br, _compile_rule_patterns(br)))


def scan_text_keyword_risks(contract_text: str) -> list[dict[str, Any]]:
    """Part 1：根据 BASIC_CONTRACT_RISK_RULES 扫描正文。"""
    if not (contract_text or "").strip():
        return []
    hits: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for rule, patterns in _COMPILED_BASIC_RULES:
        rid = str(rule.get("id") or "")
        if rid in seen_ids:
            continue
        matched = any(cre.search(contract_text) for cre in patterns)
        if matched:
            seen_ids.add(rid)
            hits.append(
                {
                    "rule_id": rid,
                    "title": str(rule.get("title") or rid),
                    "severity": str(rule.get("severity") or SEVERITY_MEDIUM),
                    "reason": str(rule.get("reason") or ""),
                }
            )
    return hits


def scan_topic_bad_pattern_risks(contract_text: str) -> list[dict[str, Any]]:
    """Part 2：主题级「不合理」关键词/正则。"""
    if not (contract_text or "").strip():
        return []
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for br, patterns in _COMPILED_TOPIC_BAD:
        rid = str(br.get("id") or "")
        if not rid or rid in seen:
            continue
        if any(cre.search(contract_text) for cre in patterns):
            seen.add(rid)
            hits.append(
                {
                    "rule_id": rid,
                    "title": str(br.get("title") or rid),
                    "severity": str(br.get("severity") or SEVERITY_MEDIUM),
                    "reason": str(br.get("reason") or ""),
                }
            )
    return hits


def _topic_keyword_hit(lower_text: str, keywords: list[str]) -> bool:
    for k in keywords:
        if not isinstance(k, str) or not k.strip():
            continue
        if k.lower() in lower_text:
            return True
    return False


def detect_covered_topic_ids(contract_text: str) -> set[str]:
    """返回正文中已覆盖的主题 topic_id 集合。"""
    if not (contract_text or "").strip():
        return set()
    lower = contract_text.lower()
    covered: set[str] = set()
    for topic in CONTRACT_CHECK_TOPICS:
        tid = str(topic.get("topic_id") or "")
        kws = [k for k in (topic.get("coverage_keywords") or []) if isinstance(k, str) and k.strip()]
        if not tid or not kws:
            continue
        if _topic_keyword_hit(lower, kws):
            covered.add(tid)
    return covered


def topic_display_name(topic_id: str) -> str:
    for t in CONTRACT_CHECK_TOPICS:
        if str(t.get("topic_id")) == topic_id:
            return str(t.get("display_name") or topic_id)
    return topic_id


def detect_contract_topic_labels(contract_text: str) -> list[str]:
    """已覆盖主题的人类可读列表（与 topic 定义顺序一致，去重）。"""
    covered_ids = detect_covered_topic_ids(contract_text)
    out: list[str] = []
    seen: set[str] = set()
    for topic in CONTRACT_CHECK_TOPICS:
        tid = str(topic.get("topic_id") or "")
        if tid in covered_ids:
            label = str(topic.get("display_name") or tid)
            if label not in seen:
                seen.add(label)
                out.append(label)
    return out


def scan_topic_missing_items(contract_text: str) -> list[str]:
    """未命中 coverage 的主题 → missing_label。"""
    if not (contract_text or "").strip():
        return []
    covered = detect_covered_topic_ids(contract_text)
    missing: list[str] = []
    for topic in CONTRACT_CHECK_TOPICS:
        tid = str(topic.get("topic_id") or "")
        if tid in covered:
            continue
        ml = str(topic.get("missing_label") or topic.get("display_name") or tid)
        if ml not in missing:
            missing.append(ml)
    return missing


def evaluate_deposit_amount_risk(
    deposit_amount: float | None,
    monthly_rent: float | None,
) -> dict[str, Any] | None:
    """
    若同时提供押金与月租：押金明显高于「五周租金」常见上限时标记风险。
    仅提供押金、无月租时不做数值比较（避免误判）。
    """
    if deposit_amount is None or monthly_rent is None:
        return None
    try:
        dep = float(deposit_amount)
        rent = float(monthly_rent)
    except (TypeError, ValueError):
        return None
    if rent <= 0 or dep < 0:
        return None

    cap = rent * _UK_FIVE_WEEKS_OF_MONTHLY_RENT
    if dep <= cap * 1.05:
        return None

    return {
        "rule_id": "deposit_amount_high",
        "title": "押金金额可能高于常见法定上限（相对月租）",
        "severity": SEVERITY_HIGH,
        "reason": (
            f"提供的押金约为 {dep:.0f}，按所填月租 {rent:.0f} 估算，"
            f"超过五周租金折算值（约 {cap:.0f}）逾 5%。"
            "英格兰对多数租约押金有上限，请核对当地现行规定与币种。"
        ),
    }


# 兼容旧名：TOPIC_MISSING_CHECKS 已并入 CONTRACT_CHECK_TOPICS
TOPIC_MISSING_CHECKS = CONTRACT_CHECK_TOPICS
