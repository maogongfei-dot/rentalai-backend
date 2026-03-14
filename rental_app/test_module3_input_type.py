# Module3 Phase1-A5-2～A5-7：input_type、analysis_mode、response_focus、guided_summary、recommended_path、next_step_hint、routing_metadata — 最小测试
# 验证三种典型输入在结果中带有正确的字段；并验证 build_routing_metadata 返回完整路由元数据

from module3_risk_result import build_contract_risk_result
from routing_metadata import build_routing_metadata

# (文本, ..., expected recommended_actions, expected action_details 关键片段, expected action_priority_map, ordered_action_details 首项关键片段)
SAMPLES = [
    ("Can my landlord increase rent?", "contract_clause", "clause_risk_review", "review_contract_risk", "contract clause for review", "contract_review_path", "审查合同条款", ["review_clause_risk", "highlight_unfair_terms"], ["不公平、模糊或偏向单方", "不合理或需要重点关注"], {"review_clause_risk": 1, "highlight_unfair_terms": 2}, "不公平、模糊或偏向单方"),
    ("The tenant must pay rent on the first day.", "contract_clause", "clause_risk_review", "review_contract_risk", "unfair, unclear, or risky", "contract_review_path", "不公平、模糊或高风险", ["review_clause_risk", "highlight_unfair_terms"], ["不公平、模糊或偏向单方", "不合理或需要重点关注"], {"review_clause_risk": 1, "highlight_unfair_terms": 2}, "不公平、模糊或偏向单方"),
    ("My landlord refused to return my deposit.", "dispute", "dispute_support", "suggest_next_steps", "dispute description", "dispute_resolution_path", "纠纷事实、证据", ["collect_evidence", "prepare_next_steps", "suggest_formal_contact"], ["聊天记录、合同、付款记录", "争议点", "正式沟通"], {"collect_evidence": 1, "prepare_next_steps": 2, "suggest_formal_contact": 3}, "聊天记录、合同、付款记录"),
]


def test_input_type_in_result():
    """三种输入均应在结果中带上正确的 ...、recommended_actions、action_details、action_priority_map、ordered_action_details（A6-1/A6-2/A6-3）。"""
    seen_summaries = set()
    for row in SAMPLES:
        text, exp_type, exp_mode, exp_focus, exp_guided_contains, exp_path, exp_hint_contains, exp_actions, exp_details_contains, exp_priority_map, exp_ordered_first = row
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
        hint = result.get("next_step_hint") or ""
        assert exp_hint_contains in hint
        guided = result.get("guided_summary") or ""
        assert exp_guided_contains in guided
        seen_summaries.add(guided)
    assert len(seen_summaries) >= 2
    print("Module3 ... / recommended_actions / action_details / action_priority_map / ordered_action_details 测试通过。")


def test_build_routing_metadata():
    """三种输入通过 build_routing_metadata 均返回完整路由元数据（含 action_priority_map、ordered_action_details），且字段正确。"""
    required_keys = ("input_type", "analysis_mode", "response_focus", "guided_summary", "recommended_path", "next_step_hint", "recommended_actions", "action_details", "action_priority_map", "ordered_action_details")
    for row in SAMPLES:
        text, exp_type, exp_mode, exp_focus, exp_guided_contains, exp_path, exp_hint_contains, exp_actions, exp_details_contains, exp_priority_map, exp_ordered_first = row
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


if __name__ == "__main__":
    test_input_type_in_result()
    test_build_routing_metadata()
