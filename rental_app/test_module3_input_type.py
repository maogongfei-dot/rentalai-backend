# Module3 Phase1-A5-2～A5-7：input_type、analysis_mode、response_focus、guided_summary、recommended_path、next_step_hint、routing_metadata — 最小测试
# 验证三种典型输入在结果中带有正确的字段；并验证 build_routing_metadata 返回完整路由元数据

from module3_risk_result import (
    build_contract_risk_result,
    build_scenario_block,
    get_evidence_required,
    get_possible_outcomes,
    get_recommended_steps,
)
from routing_metadata import build_routing_metadata

# (文本, ..., expected recommended_actions, expected action_details 关键片段, expected action_priority_map, ordered_action_details 首项关键片段, expected law_topics)
SAMPLES = [
    (
        "Can my landlord increase rent?",
        "contract_clause",
        "clause_risk_review",
        "review_contract_risk",
        "contract clause for review",
        "contract_review_path",
        "审查合同条款",
        ["review_clause_risk", "highlight_unfair_terms"],
        ["不公平、模糊或偏向单方", "不合理或需要重点关注"],
        {"review_clause_risk": 1, "highlight_unfair_terms": 2},
        "不公平、模糊或偏向单方",
        ["rent_increase"],
    ),
    (
        "The tenant must pay rent on the first day.",
        "contract_clause",
        "clause_risk_review",
        "review_contract_risk",
        "unfair, unclear, or risky",
        "contract_review_path",
        "不公平、模糊或高风险",
        ["review_clause_risk", "highlight_unfair_terms"],
        ["不公平、模糊或偏向单方", "不合理或需要重点关注"],
        {"review_clause_risk": 1, "highlight_unfair_terms": 2},
        "不公平、模糊或偏向单方",
        ["unfair_terms"],
    ),
    (
        "My landlord refused to return my deposit.",
        "dispute",
        "dispute_support",
        "suggest_next_steps",
        "dispute description",
        "dispute_resolution_path",
        "纠纷事实、证据",
        ["collect_evidence", "prepare_next_steps", "suggest_formal_contact"],
        ["聊天记录、合同、付款记录", "争议点", "正式沟通"],
        {"collect_evidence": 1, "prepare_next_steps": 2, "suggest_formal_contact": 3},
        "聊天记录、合同、付款记录",
        ["deposit_protection"],
    ),
]


def test_input_type_in_result():
    """三种输入均应在结果中带上正确的 ...、recommended_actions、action_details、action_priority_map、ordered_action_details、law_topics（Phase2-1）。"""
    seen_summaries = set()
    for row in SAMPLES:
        (
            text,
            exp_type,
            exp_mode,
            exp_focus,
            exp_guided_contains,
            exp_path,
            exp_hint_contains,
            exp_actions,
            exp_details_contains,
            exp_priority_map,
            exp_ordered_first,
            exp_law_topics,
        ) = row
        result = build_contract_risk_result(input_text=text)
        assert result.get("input_type") == exp_type
        assert result.get("analysis_mode") == exp_mode
        assert result.get("response_focus") == exp_focus
        assert result.get("recommended_path") == exp_path
        assert result.get("recommended_actions") == exp_actions
        details = result.get("action_details") or []
        assert len(details) == len(exp_actions)
        for frag in exp_details_contains:
            assert any(frag in d for d in details)
        assert result.get("action_priority_map") == exp_priority_map, f"action_priority_map 期望 {exp_priority_map!r}, 得到 {result.get('action_priority_map')!r}"
        ordered = result.get("ordered_action_details") or []
        assert len(ordered) == len(exp_actions)
        assert exp_ordered_first in (ordered[0] if ordered else ""), f"ordered_action_details 首项应包含 {exp_ordered_first!r}"
        # law_topics 至少包含预期主题
        law_topics = result.get("law_topics") or []
        for t in exp_law_topics:
            assert t in law_topics, f"law_topics 应包含 {t!r}, 得到 {law_topics!r}"
        hint = result.get("next_step_hint") or ""
        assert exp_hint_contains in hint
        guided = result.get("guided_summary") or ""
        assert exp_guided_contains in guided
        seen_summaries.add(guided)
    assert len(seen_summaries) >= 2
    print("Module3 ... / recommended_actions / action_details / action_priority_map / ordered_action_details / law_topics 测试通过。")


def test_build_routing_metadata():
    """三种输入通过 build_routing_metadata 均返回完整路由元数据（含 action_priority_map、ordered_action_details），且字段正确。"""
    required_keys = ("input_type", "analysis_mode", "response_focus", "guided_summary", "recommended_path", "next_step_hint", "recommended_actions", "action_details", "action_priority_map", "ordered_action_details")
    for row in SAMPLES:
        (
            text,
            exp_type,
            exp_mode,
            exp_focus,
            exp_guided_contains,
            exp_path,
            exp_hint_contains,
            exp_actions,
            exp_details_contains,
            exp_priority_map,
            exp_ordered_first,
            _exp_law_topics,
        ) = row
        meta = build_routing_metadata(text)
        for key in required_keys:
            assert key in meta, f"build_routing_metadata 应包含 {key!r}"
        assert meta["input_type"] == exp_type
        assert meta["recommended_path"] == exp_path
        assert meta["recommended_actions"] == exp_actions
        assert meta["action_priority_map"] == exp_priority_map
        ordered = meta.get("ordered_action_details") or []
        assert len(ordered) == len(exp_actions)
        assert exp_ordered_first in (ordered[0] if ordered else "")
        details = meta.get("action_details") or []
        for frag in exp_details_contains:
            assert any(frag in d for d in details)
        assert exp_guided_contains in (meta.get("guided_summary") or "")
        assert exp_hint_contains in (meta.get("next_step_hint") or "")
    print("build_routing_metadata 三种输入均返回完整 routing metadata（含 action_priority_map、ordered_action_details），测试通过。")


# Phase2-1 / Phase2-2：法律主题与法律依据最小测试（使用需求中的三句样例）
# (文本, 期望 law_topics, 期望 legal_references 中某条的 topic, legal_reasoning 中应包含的片段)
LAW_TOPICS_SAMPLES = [
    ("Can my landlord increase rent during the fixed term?", ["rent_increase"], "rent_increase", "房租调整条件"),
    ("The tenant must pay rent on the first day.", ["unfair_terms"], "unfair_terms", "合同条款"),
    ("My landlord refused to return my deposit.", ["deposit_protection"], "deposit_protection", "押金"),
]


def test_law_topics():
    """不同输入应生成合理的 law_topics（Phase2-1）。"""
    for row in LAW_TOPICS_SAMPLES:
        text, exp_topics, _topic, _reason_frag = row
        result = build_contract_risk_result(input_text=text)
        law_topics = result.get("law_topics") or []
        for t in exp_topics:
            assert t in law_topics, f"输入 {text!r} 的 law_topics 应包含 {t!r}, 得到 {law_topics!r}"
    print("Phase2-1 law_topics 最小测试通过。")


def test_legal_references_and_reasoning():
    """不同输入应生成合理的 legal_references 与 legal_reasoning（Phase2-2）。"""
    for row in LAW_TOPICS_SAMPLES:
        text, exp_topics, exp_ref_topic, exp_reason_frag = row
        result = build_contract_risk_result(input_text=text)
        law_topics = result.get("law_topics") or []
        for t in exp_topics:
            assert t in law_topics
        refs = result.get("legal_references") or []
        topics_in_refs = [r.get("topic") for r in refs if isinstance(r, dict) and r.get("topic")]
        assert exp_ref_topic in topics_in_refs, f"legal_references 应包含 topic={exp_ref_topic!r}, 得到 {topics_in_refs!r}"
        reasoning = result.get("legal_reasoning") or []
        assert any(exp_reason_frag in r for r in reasoning), f"legal_reasoning 中应有包含 {exp_reason_frag!r} 的项, 得到 {reasoning!r}"
    print("Phase2-2 legal_references / legal_reasoning 最小测试通过。")


def test_legal_summary():
    """不同输入应生成合理的 legal_summary（Phase2-3）：非空且包含法律主题/参考依据或相关关键词。"""
    for row in LAW_TOPICS_SAMPLES:
        text, _exp_topics, _topic, reason_frag = row
        result = build_contract_risk_result(input_text=text)
        summary = result.get("legal_summary") or ""
        assert isinstance(summary, str), "legal_summary 应为 str"
        assert len(summary.strip()) > 0, f"输入 {text!r} 的 legal_summary 不应为空"
        # 应包含组合内容：法律主题或参考依据，以及与该条相关的 reasoning 片段
        assert "法律主题" in summary or "参考依据" in summary or reason_frag in summary, (
            f"legal_summary 应包含法律主题/参考依据或片段 {reason_frag!r}, 得到: {summary[:200]!r}..."
        )
    print("Phase2-3 legal_summary 最小测试通过。")


# Phase3-1：场景识别最小测试（使用需求中的三句样例）
SCENARIO_SAMPLES = [
    ("Can my landlord increase rent during the fixed term?", "rent_increase"),
    ("The landlord may increase the rent by giving one month notice.", "rent_increase"),
    ("My landlord refused to return my deposit.", "deposit_dispute"),
]


def test_scenario_detection():
    """不同输入应生成合理的 scenario（Phase3-1）。"""
    for text, exp_scenario in SCENARIO_SAMPLES:
        result = build_contract_risk_result(input_text=text)
        scenario = result.get("scenario") or ""
        assert scenario == exp_scenario, f"输入 {text!r} 的 scenario 期望 {exp_scenario!r}, 得到 {scenario!r}"
    print("Phase3-1 scenario 最小测试通过。")


def test_evidence_required():
    """不同输入应生成合理的 evidence_required（Phase3-2），与 scenario 一致。"""
    for text, exp_scenario in SCENARIO_SAMPLES:
        result = build_contract_risk_result(input_text=text)
        scenario = result.get("scenario") or ""
        assert scenario == exp_scenario
        evidence = result.get("evidence_required") or []
        expected = get_evidence_required(exp_scenario)
        assert evidence == expected, f"输入 {text!r} 的 evidence_required 期望 {expected!r}, 得到 {evidence!r}"
    print("Phase3-2 evidence_required 最小测试通过。")


def test_recommended_steps():
    """不同输入应生成合理的 recommended_steps（Phase3-3），与 scenario 一致。"""
    for text, exp_scenario in SCENARIO_SAMPLES:
        result = build_contract_risk_result(input_text=text)
        scenario = result.get("scenario") or ""
        assert scenario == exp_scenario
        steps = result.get("recommended_steps") or []
        expected = get_recommended_steps(exp_scenario)
        assert steps == expected, f"输入 {text!r} 的 recommended_steps 期望 {expected!r}, 得到 {steps!r}"
    print("Phase3-3 recommended_steps 最小测试通过。")


def test_possible_outcomes():
    """不同输入应生成合理的 possible_outcomes（Phase3-4），与 scenario 一致。"""
    for text, exp_scenario in SCENARIO_SAMPLES:
        result = build_contract_risk_result(input_text=text)
        scenario = result.get("scenario") or ""
        assert scenario == exp_scenario
        outcomes = result.get("possible_outcomes") or []
        expected = get_possible_outcomes(exp_scenario)
        assert outcomes == expected, f"输入 {text!r} 的 possible_outcomes 期望 {expected!r}, 得到 {outcomes!r}"
    print("Phase3-4 possible_outcomes 最小测试通过。")


def test_scenario_block():
    """不同输入应稳定生成完整的场景闭环 scenario_block（Phase3 Final）。"""
    for text, exp_scenario in SCENARIO_SAMPLES:
        result = build_contract_risk_result(input_text=text)
        block = result.get("scenario_block")
        assert block is not None, f"输入 {text!r} 应有 scenario_block"
        assert isinstance(block, dict), "scenario_block 应为 dict"
        for key in ("scenario", "evidence_required", "recommended_steps", "possible_outcomes"):
            assert key in block, f"scenario_block 应包含键 {key!r}"
        assert block["scenario"] == exp_scenario, f"输入 {text!r} 的 scenario_block.scenario 期望 {exp_scenario!r}, 得到 {block['scenario']!r}"
        assert block["evidence_required"] == (result.get("evidence_required") or []), "scenario_block 与扁平字段 evidence_required 一致"
        assert block["recommended_steps"] == (result.get("recommended_steps") or []), "scenario_block 与扁平字段 recommended_steps 一致"
        assert block["possible_outcomes"] == (result.get("possible_outcomes") or []), "scenario_block 与扁平字段 possible_outcomes 一致"
        # 与 build_scenario_block 返回值一致
        expected_block = build_scenario_block(
            result["scenario"],
            result.get("evidence_required") or [],
            result.get("recommended_steps") or [],
            result.get("possible_outcomes") or [],
        )
        assert block == expected_block, f"scenario_block 应与 build_scenario_block(...) 一致"
    print("Phase3 Final scenario_block 最小测试通过。")


if __name__ == "__main__":
    test_input_type_in_result()
    test_build_routing_metadata()
    test_law_topics()
    test_legal_references_and_reasoning()
    test_legal_summary()
    test_scenario_detection()
    test_evidence_required()
    test_recommended_steps()
    test_possible_outcomes()
    test_scenario_block()
