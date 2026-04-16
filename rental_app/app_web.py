"""旧的 / 辅助的 RentalAI Streamlit 界面入口（历史迭代见文末简述）。

定位（勿与主产品混淆）
----------------------
- 本文件是 **旧的 / 辅助的** Streamlit UI 入口，**不是**当前 FastAPI 主产品的前端入口。
- **当前主产品本地推荐入口：** ``run.py``（本地以该入口为主线之一）。
- **当前主后端应用：** ``api_server.py`` 中定义的 FastAPI 应用（ASGI）；HTTP 能力以此为中心。
- **本文件用途：** 历史兼容、辅助演示或内部测试；**后续主线开发默认不再以本文件为核心**。

为何仍保留 / 为何不是主线 / 与 run.py、api_server.py 的关系
------------------------------------------------------------
- **仍保留：** 维持一套可独立用 ``streamlit run`` 启动的界面，便于对照旧流程、做演示验收或内部测试，
  而不删除已积累的表单与展示逻辑。
- **不是主线：** 主力交付形态以 API（``api_server.py``）及围绕其的客户端/集成为主，而非以本
  Streamlit 单页为唯一或核心产品面。
- **与 ``run.py``：** ``run.py`` 是本地推荐的统一启动/编排入口；本文件是 **仅 Streamlit**
  的另一条路，二者勿混为一谈。
- **与 ``api_server.py``：** 侧栏关闭「本地引擎」时，本 UI 通过 HTTP 调用后端；该后端即为
  ``api_server.py`` 暴露的应用。勾选本地引擎时则在进程内走分析，用于无需起 API 的快速试用。

如何启动（在 ``rental_app`` 目录下）::

    streamlit run app_web.py

- 浏览器默认: http://localhost:8501
- 依赖: ``pip install -r requirements.txt``（含 streamlit）

实现背景（原顶部注释归档）
--------------------------
P1 Phase1–6 + P2 Phase1–4 + P4 Phase1–5 + P5 Phase1–5：Web UI（Agent 收口 + Product 层）；
Phase4：结果解释增强（推荐 / 顾虑 / 风险 / 下一步分开展示）；Phase5：输入校验、示例预填、错误提示、
Reset form；Phase6：页面收口、统一文案、演示顺序、弱化调试区。
"""
# 提示：主线开发与集成请以 run.py + api_server.py 为准；本文件为 Streamlit 兼容/演示/测试保留。

import logging
import os

import streamlit as st

_ui_logger = logging.getLogger("rentalai.ui")
if not _ui_logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

from alert_utils import FailureTracker, send_alert
from config import get_bind_port, get_default_api_url_for_tools

_ui_api_failures = FailureTracker(threshold=3, source="streamlit-ui")

from web_ui.condition_summary import summarize_analyze_context, summarize_batch_request
from web_ui.listing_detail_panel import build_analyze_detail_bundle, build_batch_detail_bundle
from web_ui.listing_result_card import (
    build_analyze_card_model,
    build_batch_row_card_model,
    render_listing_result_card,
)
from web_ui.agent_entry import render_p5_agent_entry
from web_ui.rental_intent import AgentRentalRequest
from web_ui.real_analysis_service import run_real_listings_analysis, run_real_listings_analysis_async
from web_ui.agent_insight_summary import build_agent_insight_bundle, resolve_intent_for_insights
from web_ui.agent_summary_panel import render_agent_insight_panel
from web_ui.batch_results_view import render_batch_partitioned_listings
from web_ui.product_copy import DISPLAY_LABELS
from web_ui.result_filters import collect_source_values, collect_top_indices, filter_batch_rows
from web_ui.result_sorters import sort_batch_rows
from web_ui.result_ui import section_header
from data.explain.rule_explain import build_p10_explain_for_batch_row
from web_ui.p10_features import batch_row_compare_label, batch_row_to_favorite_payload

# ---------- P1 Phase5: 输入校验 / 示例数据 / 错误提示 ----------

# Session keys for form widgets（与 st.text_input(..., key=) 一致）
_FORM_KEYS = {
    "rent": "form_rent",
    "budget": "form_budget",
    "commute_minutes": "form_commute_minutes",
    "bedrooms": "form_bedrooms",
    "distance": "form_distance",
    "bills_included": "form_bills_included",
    "area": "form_area",
    "postcode": "form_postcode",
    "target_postcode": "form_target_postcode",
}

# 推荐示例（与需求一致）；首次进入页面会预填
_DEMO_FORM_STATE = {
    _FORM_KEYS["rent"]: "1200",
    _FORM_KEYS["budget"]: "1500",
    _FORM_KEYS["commute_minutes"]: "25",
    _FORM_KEYS["bedrooms"]: "2",
    _FORM_KEYS["distance"]: "",
    _FORM_KEYS["bills_included"]: True,
    _FORM_KEYS["area"]: "",
    _FORM_KEYS["postcode"]: "",
    _FORM_KEYS["target_postcode"]: "",
}

# Clear form：空字符串 + bills 关（用户需自行填写或再点 Load example）
_CLEAR_FORM_STATE = {
    _FORM_KEYS["rent"]: "",
    _FORM_KEYS["budget"]: "",
    _FORM_KEYS["commute_minutes"]: "",
    _FORM_KEYS["bedrooms"]: "",
    _FORM_KEYS["distance"]: "",
    _FORM_KEYS["bills_included"]: False,
    _FORM_KEYS["area"]: "",
    _FORM_KEYS["postcode"]: "",
    _FORM_KEYS["target_postcode"]: "",
}


def init_form_session_state() -> None:
    """首次访问时预填示例数据（不覆盖用户已改过的 session）。"""
    for k, v in _DEMO_FORM_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_demo_values() -> dict:
    """返回示例表单状态副本（供 Load example 批量写回）。"""
    return dict(_DEMO_FORM_STATE)


def _parse_non_negative_float(raw: str, field_label: str) -> tuple[float | None, str | None]:
    """解析非负浮点；错误返回 (None, error_message)。"""
    s = (raw or "").strip()
    if not s:
        return None, f"{field_label} is required"
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None, f"{field_label} must be a numeric value"
    if v < 0:
        return None, f"{field_label} must be a non-negative number"
    return v, None


def _parse_non_negative_int(raw: str, field_label: str) -> tuple[int | None, str | None]:
    """解析非负整数（允许 2.0 这类输入）。"""
    s = (raw or "").strip()
    if not s:
        return None, f"{field_label} is required"
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None, f"{field_label} must be a numeric value"
    if v < 0:
        return None, f"{field_label} must be a non-negative number"
    return int(v), None


def validate_inputs(raw: dict) -> tuple[bool, list[str]]:
    """
    Phase5 基础校验：rent/budget/commute/bedrooms 必填、数字、>=0；
    bills_included 可布尔化；area/postcode/target_postcode/distance 可空，不报错。
    """
    errors: list[str] = []
    rent = raw.get("rent")
    budget = raw.get("budget")
    commute = raw.get("commute_minutes")
    bedrooms = raw.get("bedrooms")
    bills = raw.get("bills_included")

    _, e = _parse_non_negative_float(str(rent) if rent is not None else "", "Rent (£/month)")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_float(str(budget) if budget is not None else "", "Budget (£/month)")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_int(str(commute) if commute is not None else "", "Commute minutes")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_int(str(bedrooms) if bedrooms is not None else "", "Bedrooms")
    if e:
        errors.append(e)

    # Checkbox 一般为 bool；若来自其它来源则尝试转换
    if bills is None:
        errors.append("Bills included must be yes/no or a checkbox value")
    elif isinstance(bills, str):
        sl = bills.strip().lower()
        if sl not in ("", "yes", "y", "true", "1", "no", "n", "false", "0", "包", "包含"):
            if sl:  # 非空且无法识别
                errors.append("Bills included must be a clear yes/no value")

    return (len(errors) == 0, errors)


def build_error_message(errors: list[str]) -> str:
    """合并为一段可读错误文案（单行换行展示）。"""
    if not errors:
        return ""
    return "\n".join(f"• {e}" for e in errors)


def collect_raw_form_from_session() -> dict:
    """从 session_state 组装与原先 raw_form 相同结构的 dict。"""
    return {
        "rent": st.session_state.get(_FORM_KEYS["rent"], ""),
        "budget": st.session_state.get(_FORM_KEYS["budget"], ""),
        "commute_minutes": st.session_state.get(_FORM_KEYS["commute_minutes"], ""),
        "bedrooms": st.session_state.get(_FORM_KEYS["bedrooms"], ""),
        "distance": st.session_state.get(_FORM_KEYS["distance"], ""),
        "bills_included": st.session_state.get(_FORM_KEYS["bills_included"], False),
        "area": st.session_state.get(_FORM_KEYS["area"], ""),
        "postcode": st.session_state.get(_FORM_KEYS["postcode"], ""),
        "target_postcode": st.session_state.get(_FORM_KEYS["target_postcode"], ""),
    }


def normalize_form_values(raw: dict) -> dict:
    """校验通过后交给 web_bridge 做类型与空字段规范化（与引擎入参对齐）。"""
    from web_bridge import normalize_web_form_inputs

    return normalize_web_form_inputs(raw)


def run_analysis_for_ui(
    raw_form: dict,
    *,
    use_local: bool,
    api_base_url: str,
    api_endpoint: str = "/analyze",
    auth_token: str | None = None,
) -> tuple[dict | None, str | None]:
    """
    P2 Phase3：HTTP 可调 /analyze、/score-breakdown、/risk-check、/explain-only；
    本地模式等价全量 /analyze。
    """
    from api_analysis import envelope_from_engine_result, legacy_ui_result_from_standard_envelope

    import time as _time

    if use_local:
        try:
            from web_bridge import run_web_demo_analysis

            _t0 = _time.perf_counter()
            input_data = normalize_form_values(raw_form)
            engine = run_web_demo_analysis(input_data)
            _dur = _time.perf_counter() - _t0
            _ui_logger.info("[PERF] local engine %s took %.3fs", api_endpoint, _dur)
            if _dur > 10.0:
                _ui_logger.warning("[PERF][SLOW] local engine %s took %.1fs", api_endpoint, _dur)
            envelope = envelope_from_engine_result(engine)
            return legacy_ui_result_from_standard_envelope(envelope), None
        except Exception as e:
            _ui_logger.error("Local engine failed | endpoint=%s | error=%s", api_endpoint, e)
            return None, "Analysis engine error: %s" % e

    import requests

    path = api_endpoint if str(api_endpoint).startswith("/") else "/%s" % api_endpoint
    url = "%s%s" % ((api_base_url or "").rstrip("/"), path)
    try:
        _t0 = _time.perf_counter()
        headers = {"Authorization": "Bearer %s" % auth_token} if auth_token else None
        resp = requests.post(url, json=raw_form, timeout=120, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        _dur = _time.perf_counter() - _t0
        _ui_logger.info("[PERF] HTTP %s -> %s in %.3fs", path, resp.status_code, _dur)
        if not isinstance(data, dict):
            return None, "API returned non-JSON object"
        _ui_api_failures.record_success(path)
        return legacy_ui_result_from_standard_envelope(data), None
    except requests.RequestException as e:
        _ui_logger.error("API request failed | url=%s | error=%s", url, e)
        _ui_api_failures.record_failure(path, str(e))
        return None, "API request failed: %s" % (e,)
    except ValueError as e:
        _ui_logger.error("Invalid JSON from API | url=%s | error=%s", url, e)
        _ui_api_failures.record_failure(path, str(e))
        return None, "Invalid JSON from API: %s" % (e,)


# ---------- P1 Phase6: Demo 收口 / 统一展示文案 ----------


def normalize_display_labels() -> dict:
    """P4 Phase5：与 `web_ui.product_copy.DISPLAY_LABELS` 同步的展示文案。"""
    return dict(DISPLAY_LABELS)


def build_page_header(*, show_demo_hint: bool = True) -> None:
    """主标题 + 一句话产品说明；可选 Demo 引导（不抢主视觉）。"""
    st.title("RentalAI · Rental decision demo")
    st.markdown(
        "Compare a listing to your **budget** and **commute**, then review **overview**, "
        "**property score**, **decision**, and **recommended reasons**, **concerns**, **risks**, and **next steps**."
    )
    if show_demo_hint:
        st.caption(
            "Demo: sample values are pre-filled — click **Analyze Property** for a one-click run."
        )


def render_criteria_summary(lines: list[tuple[str, str]], *, empty_caption: str) -> None:
    """P4 Phase2: 轻量条件摘要（Markdown 一行）。"""
    if not lines:
        st.caption(empty_caption)
        return
    st.markdown(" · ".join("**%s:** %s" % (lab, val) for lab, val in lines))


def render_demo_footer() -> None:
    """页脚 prototype 声明（Phase6 验收用）。"""
    st.markdown("---")
    st.caption(
        "_This is a prototype demo for rental property analysis. "
        "Results are illustrative and not legal, financial, or investment advice._"
    )
    st.caption("RentalAI P1 · Module2 + Module7 · Web UI")


# ---------- P1 Phase3: 安全展示辅助函数 ----------


def safe_get(obj, *keys, default="N/A"):
    """嵌套 dict 安全取值；缺省或空返回 default。"""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    if cur is None:
        return default
    if isinstance(cur, str) and not cur.strip():
        return default
    if isinstance(cur, (list, dict)) and len(cur) == 0:
        return default
    return cur


def _display_text(val, empty="No data"):
    """标量转展示字符串。"""
    if val is None:
        return empty
    if isinstance(val, str) and not val.strip():
        return empty
    return str(val)


def format_decision_block(decision: dict) -> None:
    """payload.decision 结构化展示（非 raw 一行）。"""
    if not isinstance(decision, dict) or not decision:
        st.caption("No data")
        return
    for key in (
        "final_summary",
        "decision_focus",
        "final_action",
        "house_signal",
        "risk_signal",
    ):
        label = key.replace("_", " ").title()
        val = decision.get(key)
        st.markdown(f"**{label}**")
        st.write(_display_text(val, "N/A"))


def format_analysis_block(analysis: dict) -> None:
    """payload.analysis：列表用 bullet，dict 嵌套简短展示。"""
    if not isinstance(analysis, dict) or not analysis:
        st.caption("Empty")
        return
    for key, val in analysis.items():
        label = str(key).replace("_", " ").title()
        st.markdown(f"**{label}**")
        if isinstance(val, list):
            if not val:
                st.caption("Empty")
            else:
                for item in val:
                    if isinstance(item, (dict, list)):
                        st.json(item)
                    else:
                        st.markdown(f"- {_display_text(item, 'N/A')}")
        elif isinstance(val, dict):
            if not val:
                st.caption("Empty")
            else:
                st.json(val)
        else:
            st.write(_display_text(val, "N/A"))


def format_user_facing_block(uf: dict) -> None:
    """用户可读解释区。"""
    if not isinstance(uf, dict) or not uf:
        st.caption("No data")
        return
    summary = uf.get("summary")
    st.markdown("**Summary**")
    st.info(_display_text(summary, "N/A"))

    list_keys = ("reason", "risk_note", "next_step", "explanation")
    for lk in list_keys:
        items = uf.get(lk) or []
        title = lk.replace("_", " ").title()
        st.markdown(f"**{title}**")
        if not isinstance(items, list):
            st.write(_display_text(items, "N/A"))
        elif not items:
            st.caption("Empty")
        else:
            for x in items:
                st.markdown(f"- {_display_text(x, 'N/A')}")


def format_references_block(refs: dict) -> None:
    """references 分区展示。"""
    if not isinstance(refs, dict) or not refs:
        st.caption("No data")
        return
    for name in ("house_reference", "risk_reference"):
        sub = refs.get(name)
        st.markdown(f"**{name.replace('_', ' ').title()}**")
        if not isinstance(sub, dict) or not sub:
            st.caption("Empty")
        else:
            for k, v in sub.items():
                st.markdown(f"- **{k}:** {_display_text(v, 'N/A')}")


def format_trace_block(trace: dict, *, compact: bool = True) -> None:
    """Trace 调试向展示。"""
    if not isinstance(trace, dict) or not trace:
        st.caption("Empty")
        return
    ts = trace.get("trace_summary")
    st.markdown("**Trace summary**")
    st.write(_display_text(ts, "N/A"))
    list_fields = (
        ("decision_trace", "Decision trace"),
        ("blocker_trace", "Blocker trace"),
        ("support_trace", "Support trace"),
        ("house_trace_reasons", "House trace"),
        ("risk_trace_reasons", "Risk trace"),
    )
    for field, title in list_fields:
        lst = trace.get(field) or []
        st.markdown(f"**{title}**")
        if not isinstance(lst, list) or not lst:
            st.caption("Empty")
        else:
            show = lst[:4] if compact else lst
            for line in show:
                st.markdown(f"- {_display_text(line, 'N/A')}")


# ---------- P1 Phase4: 解释层提取与格式化 ----------


def _list_str(v):
    """任意值 → 非空字符串列表。"""
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    return []


def _dedupe_preserve(items: list) -> list:
    """去重保序，忽略大小写键。"""
    seen = set()
    out = []
    for x in items:
        if not isinstance(x, str):
            continue
        k = x.strip().lower()
        if not k or k in ("n/a", "none", "empty"):
            continue
        if k not in seen:
            seen.add(k)
            out.append(x.strip())
    return out


def extract_recommended_reasons(
    decision: dict,
    analysis: dict,
    user_facing: dict,
    trace: dict,
    result: dict,
) -> list:
    """合并 user_facing / analysis / trace / explanation_snapshot 中的正向理由。"""
    out = []
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("supporting_reasons")))
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("reason")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("support_trace")))
        out.extend(_list_str(trace.get("house_trace_reasons")))
    expl = (result or {}).get("explanation_summary") or {}
    if isinstance(expl, dict):
        out.extend(_list_str(expl.get("key_positives")))
        out.extend(_list_str(expl.get("top_positive_reasons")))
        out.extend(_list_str(expl.get("why_recommend")))
    # final_recommendation 主理由一句
    frec = (result or {}).get("final_recommendation") or {}
    if isinstance(frec, dict):
        pr = frec.get("primary_recommendation") or {}
        if isinstance(pr, dict) and pr.get("reason"):
            out.extend(_list_str(pr.get("reason")))
    return _dedupe_preserve(out)


def extract_concerns(decision: dict, analysis: dict, user_facing: dict, trace: dict) -> list:
    """顾虑 / 为何不直接推进：blockers、缺失信息、局限、风险侧 trace。"""
    out = []
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("primary_blockers")))
        out.extend(_list_str(analysis.get("missing_information")))
        out.extend(_list_str(analysis.get("assessment_limitations")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("blocker_trace")))
        out.extend(_list_str(trace.get("risk_trace_reasons")))
    expl = (user_facing or {}).get("explanation") if isinstance(user_facing, dict) else []
    # explanation 链里常含 “However …” — 整段作为一条补充顾虑（避免拆句复杂逻辑）
    for line in _list_str(expl):
        if any(w in line.lower() for w in ("however", "unsafe", "not yet", "clarify", "missing", "gap", "unresolved")):
            out.append(line)
    return _dedupe_preserve(out)


def extract_risks(analysis: dict, user_facing: dict, trace: dict, references: dict) -> list:
    """风险提示：用户 risk_note + 参考摘要中的警示。"""
    out = []
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("risk_note")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("blocker_trace")))
    if isinstance(references, dict):
        for key in ("house_reference", "risk_reference"):
            sub = references.get(key) or {}
            if isinstance(sub, dict):
                summ = sub.get("summary") or sub.get("risk_level")
                out.extend(_list_str(summ) if isinstance(summ, str) else _list_str(summ))
    return _dedupe_preserve(out)


def extract_next_steps(decision: dict, user_facing: dict, analysis: dict) -> list:
    """下一步用户指引：final_action + next_step + 必做动作 + 建议补充信息。"""
    out = []
    if isinstance(decision, dict):
        out.extend(_list_str(decision.get("final_action")))
        out.extend(_list_str(decision.get("decision_focus")))
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("next_step")))
        out.extend(_list_str(user_facing.get("explanation")))
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("required_actions_before_proceeding")))
        out.extend(_list_str(analysis.get("recommended_inputs_to_improve_decision")))
    return _dedupe_preserve(out)


def format_reason_list(title: str, reasons: list, *, empty_label: str = "No clear reason provided") -> None:
    """统一 bullet 展示理由列表。"""
    if title and str(title).strip():
        st.markdown(f"**{title}**")
    if not reasons:
        st.caption(empty_label)
        return
    for r in reasons:
        st.markdown(f"- {_display_text(r, 'N/A')}")


def render_explanation_highlights(
    decision: dict,
    analysis: dict,
    user_facing: dict,
    trace: dict,
    references: dict,
    result: dict,
) -> None:
    """Phase4/6 解释区：纵向顺序 — Recommended → Concerns → Risks → Next steps（与验收顺序一致）。"""
    lab = normalize_display_labels()
    rec = extract_recommended_reasons(decision, analysis, user_facing, trace, result)
    con = extract_concerns(decision, analysis, user_facing, trace)
    risks = extract_risks(analysis, user_facing, trace, references)
    steps = extract_next_steps(decision, user_facing, analysis)

    st.markdown(f"## {lab['recommended']}")
    st.caption("Why the engine leans positive (when data supports it).")
    format_reason_list("", rec)
    if rec:
        st.success("These factors support moving forward (subject to your own checks).")
    elif not (con or risks or steps):
        st.caption("No structured positive reasons extracted for this run.")

    st.divider()
    st.markdown(f"## {lab['concerns']}")
    st.caption("Gaps, blockers, or reasons to pause before committing.")
    format_reason_list("", con)
    if con:
        st.warning("Review these before you proceed.")

    st.divider()
    st.markdown(f"## {lab['risks']}")
    st.caption("Uncertainty and downside signals.")
    format_reason_list("", risks)
    if risks:
        st.error("Treat these as signals to verify or mitigate.")

    st.divider()
    st.markdown(f"## {lab['next_steps']}")
    st.caption("Concrete follow-ups from the decision and user-facing guidance.")
    format_reason_list("", steps)
    if steps:
        st.info("Work through these in order where relevant.")

    if not rec and not con and not risks and not steps:
        st.caption("No structured explanation blocks were extracted from this run.")


# ---------- 页面配置 ----------

st.set_page_config(page_title="RentalAI Demo", page_icon="🏠", layout="wide")

init_form_session_state()

lab = normalize_display_labels()
build_page_header(show_demo_hint=True)

# --- P2：侧栏 API / 本地 + 可选子接口路径 ---
st.sidebar.markdown("### Backend (P2)")
_use_local = st.sidebar.checkbox(
    "Use local engine (bypass API)",
    value=os.environ.get("RENTALAI_USE_LOCAL", "").strip().lower() in ("1", "true", "yes"),
    help="On = in-process full analysis (same as /analyze). Modular paths require API.",
)
_api_default = get_default_api_url_for_tools()
_api_base = st.sidebar.text_input(
    "API base URL",
    value=_api_default,
    disabled=_use_local,
    help="Env: RENTALAI_API_URL (deploy), or RENTALAI_PUBLIC_API_HOST + RENTALAI_PORT/PORT for local default.",
)
_api_endpoint = st.sidebar.selectbox(
    "API endpoint",
    options=["/analyze", "/score-breakdown", "/risk-check", "/explain-only"],
    index=0,
    disabled=_use_local,
    help="P2 Phase3 modular APIs; default /analyze keeps full dashboard data.",
)
if _use_local:
    st.sidebar.caption("Local mode always uses full engine output (≈ POST /analyze).")
if _api_default.startswith("http://127.") or _api_default.startswith("http://localhost"):
    st.sidebar.caption(
        "Start API: `python run.py` or `uvicorn api_server:app --host 127.0.0.1 --port %s`"
        % get_bind_port()
    )
else:
    st.sidebar.caption("API: **%s**" % _api_default)

# --- P10 Phase2: minimal auth (register/login) ---
st.sidebar.markdown("### User (P10 minimal auth)")
_auth_email = st.sidebar.text_input("Email", value=st.session_state.get("auth_email", ""), key="auth_email")
_auth_password = st.sidebar.text_input("Password", value="", type="password", key="auth_password")
_auth_token = st.session_state.get("auth_token")
_auth_user_id = st.session_state.get("auth_user_id")
_auth_msg = ""
if st.sidebar.button("Register", key="auth_register_btn", disabled=_use_local):
    import requests as _req
    try:
        _resp = _req.post(
            "%s/auth/register" % _api_base.rstrip("/"),
            json={"email": _auth_email, "password": _auth_password},
            timeout=15,
        )
        if _resp.status_code >= 400:
            _auth_msg = "Register failed: %s" % _resp.text
        else:
            _auth_msg = "Register success. Please login."
    except Exception as _ex:  # noqa: BLE001
        _auth_msg = "Register error: %s" % _ex
if st.sidebar.button("Login", key="auth_login_btn", disabled=_use_local):
    import requests as _req
    try:
        _resp = _req.post(
            "%s/auth/login" % _api_base.rstrip("/"),
            json={"email": _auth_email, "password": _auth_password},
            timeout=15,
        )
        if _resp.status_code >= 400:
            _auth_msg = "Login failed: %s" % _resp.text
            st.session_state.pop("auth_token", None)
            st.session_state.pop("auth_user_id", None)
        else:
            _bj = _resp.json()
            st.session_state["auth_token"] = _bj.get("token")
            st.session_state["auth_user_id"] = _bj.get("user_id")
            _auth_token = st.session_state.get("auth_token")
            _auth_user_id = st.session_state.get("auth_user_id")
            _auth_msg = "Login success."
    except Exception as _ex:  # noqa: BLE001
        _auth_msg = "Login error: %s" % _ex
if st.sidebar.button("Logout", key="auth_logout_btn"):
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user_id", None)
    _auth_token = None
    _auth_user_id = None
    _auth_msg = "Logged out."
if _auth_user_id:
    st.sidebar.caption("Current user: `%s`" % _auth_user_id)
elif not _use_local:
    st.sidebar.caption("Please login for async tasks and history queries.")
if _auth_msg:
    st.sidebar.caption(_auth_msg)

# --- P10 Phase2: history + favorites (sidebar) ---
st.sidebar.markdown("### P10 · History & favorites")
with st.sidebar.expander("Load history / saved list", expanded=False):
    if _use_local:
        st.caption("Turn off **local engine** and use the API for history & favorites.")
    elif not _auth_token:
        st.caption("Login above to fetch task/analysis history and favorites.")
    else:
        import requests as _req_p10

        _bu_p10 = _api_base.rstrip("/")
        _h_p10 = {"Authorization": "Bearer %s" % _auth_token}
        if st.button("Refresh task + analysis history", key="p10_sidebar_hist"):
            try:
                st.session_state["p10_hist_tasks"] = _req_p10.get(
                    "%s/records/tasks" % _bu_p10, headers=_h_p10, params={"limit": 15}, timeout=30
                ).json()
                st.session_state["p10_hist_analysis"] = _req_p10.get(
                    "%s/records/analysis" % _bu_p10, headers=_h_p10, params={"limit": 15}, timeout=30
                ).json()
                st.session_state.pop("p10_sidebar_err", None)
            except Exception as _ex_p10:  # noqa: BLE001
                st.session_state["p10_sidebar_err"] = str(_ex_p10)
        if st.button("Load my favorites", key="p10_sidebar_fav"):
            try:
                st.session_state["p10_favorites"] = _req_p10.get(
                    "%s/favorites" % _bu_p10, headers=_h_p10, timeout=30
                ).json()
                st.session_state.pop("p10_sidebar_err", None)
            except Exception as _ex_p10:  # noqa: BLE001
                st.session_state["p10_sidebar_err"] = str(_ex_p10)
        if st.session_state.get("p10_sidebar_err"):
            st.warning(st.session_state["p10_sidebar_err"])
        _ht = st.session_state.get("p10_hist_tasks")
        if isinstance(_ht, dict) and _ht.get("records") is not None:
            st.caption("Tasks (latest first): **%s** rows" % _ht.get("count", 0))
            st.dataframe(_ht.get("records") or [], use_container_width=True, hide_index=True)
        _ha = st.session_state.get("p10_hist_analysis")
        if isinstance(_ha, dict) and _ha.get("records") is not None:
            st.caption("Analysis records: **%s** rows" % _ha.get("count", 0))
            st.dataframe(_ha.get("records") or [], use_container_width=True, hide_index=True)
        _fv = st.session_state.get("p10_favorites")
        if isinstance(_fv, dict) and _fv.get("favorites") is not None:
            st.caption("Saved favorites: **%s**" % _fv.get("count", 0))
            _frows = _fv.get("favorites") or []
            if _frows:
                st.dataframe(_frows, use_container_width=True, hide_index=True)
                _del_id = st.text_input("Remove favorite by id", key="p10_fav_del_id")
                if st.button("Delete favorite", key="p10_fav_del_btn"):
                    try:
                        _dr = _req_p10.delete(
                            "%s/favorites/%s" % (_bu_p10, _del_id.strip()),
                            headers=_h_p10,
                            timeout=20,
                        )
                        if _dr.status_code >= 400:
                            st.warning(_dr.text)
                        else:
                            st.success("Removed.")
                            st.session_state.pop("p10_favorites", None)
                    except Exception as _ex_p10:  # noqa: BLE001
                        st.warning(str(_ex_p10))

# --- P7 Phase5: 真实多平台抓取 + batch（侧栏控制 Agent 与 batch 区按钮）---
st.sidebar.markdown("### %s" % lab.get("p7_sidebar_title", "Real listings (P7)"))
st.sidebar.caption(lab.get("p7_sidebar_caption", ""))
st.sidebar.number_input(
    lab.get("p7_limit_label", "Listings per portal"),
    min_value=1,
    max_value=25,
    value=int(st.session_state.get("p7_limit_per_source", 8)),
    step=1,
    key="p7_limit_per_source",
)
st.sidebar.checkbox(
    lab.get("p7_headless_label", "Headless browser"),
    value=bool(st.session_state.get("p7_headless", True)),
    key="p7_headless",
)
st.sidebar.checkbox(
    lab.get("p7_persist_label", "Persist listings"),
    value=bool(st.session_state.get("p7_persist_listings", True)),
    key="p7_persist_listings",
)
st.sidebar.checkbox(
    "Async mode (pilot)",
    value=bool(st.session_state.get("p7_async_pilot", False)),
    key="p7_async_pilot",
    help="Run analysis via backend async task (POST /tasks). Requires API to be running.",
)

_p7_lim = int(st.session_state.get("p7_limit_per_source", 8))
_p7_h = bool(st.session_state.get("p7_headless", True))
_p7_persist = bool(st.session_state.get("p7_persist_listings", True))
_p7_async = bool(st.session_state.get("p7_async_pilot", False))

# --- P5 + P7：Agent 入口（自然语言 → 预览 → 真实多平台抓取 + batch）---
render_p5_agent_entry(
    st,
    lab=lab,
    form_keys=_FORM_KEYS,
    use_local=_use_local,
    api_base_url=_api_base,
    limit_per_source=_p7_lim,
    headless=_p7_h,
    persist_listings=_p7_persist,
    async_mode=_p7_async,
    auth_token=_auth_token,
)

# --- Phase6: 输入区（表单 → 再操作按钮，顺序与验收一致）---
st.subheader(lab["input_section"])
st.caption(
    "Required: rent, budget, commute, and bedrooms (non-negative numbers). "
    "Optional: area, postcode, target postcode, distance (invalid distance is ignored server-side)."
)

c1, c2, c3 = st.columns(3)
with c1:
    st.text_input("Rent (£/month)", key=_FORM_KEYS["rent"], help="Required, non-negative number")
    st.text_input("Budget (£/month)", key=_FORM_KEYS["budget"], help="Required, non-negative number")
    st.text_input("Commute (minutes)", key=_FORM_KEYS["commute_minutes"], help="Required, non-negative integer")
with c2:
    st.text_input("Bedrooms", key=_FORM_KEYS["bedrooms"], help="Required, non-negative integer")
    st.text_input(
        "Distance (optional)",
        key=_FORM_KEYS["distance"],
        help="Optional; non-numeric values are ignored and do not block submit",
    )
    st.checkbox("Bills included", key=_FORM_KEYS["bills_included"])
with c3:
    st.text_input("Area", key=_FORM_KEYS["area"], placeholder="e.g. E1")
    st.text_input("Postcode", key=_FORM_KEYS["postcode"], placeholder="e.g. E1 6AN")
    st.text_input("Target postcode (optional)", key=_FORM_KEYS["target_postcode"])

st.markdown("---")
st.subheader(lab["actions_section"])
ba, bb, bc = st.columns([1, 1, 2])
with ba:
    if st.button("Load Demo Data", type="secondary", help="Restore recommended sample values"):
        for k, v in load_demo_values().items():
            st.session_state[k] = v
        st.rerun()
with bb:
    if st.button("Reset Form", type="secondary", help="Clear fields; use Load Demo Data or enter values again"):
        for k, v in _CLEAR_FORM_STATE.items():
            st.session_state[k] = v
        st.rerun()
with bc:
    analyze = st.button("Analyze Property", type="primary", use_container_width=True)

if not analyze:
    st.info(lab["idle_analyze_hint"])
else:
    raw_form = collect_raw_form_from_session()

    valid, validation_errors = validate_inputs(raw_form)
    if not valid:
        st.markdown(f"### {lab['validation_section']}")
        st.error(lab["validation_intro"])
        st.warning(build_error_message(validation_errors))
        st.stop()

    result = None
    err_msg = None
    try:
        with st.spinner(lab["spinner_analyze"]):
            result, transport_err = run_analysis_for_ui(
                raw_form,
                use_local=_use_local,
                api_base_url=_api_base,
                api_endpoint=_api_endpoint,
                auth_token=_auth_token,
            )
        if transport_err:
            err_msg = transport_err
            result = result or {
                "success": False,
                "message": transport_err,
                "unified_decision_payload": {},
            }
    except Exception as e:
        err_msg = str(e)
        result = {"success": False, "message": err_msg, "unified_decision_payload": {}}

    if err_msg:
        st.markdown(f"### {lab['errors_section']}")
        st.error(lab["error_unexpected"])
        st.warning(_display_text(err_msg, lab["unknown_error"]))

    if not result:
        st.error(lab["error_no_result"])
        st.stop()

    # P2 Phase2：API 业务失败时优先展示 error.message（已映射到 result["message"]）
    if not err_msg and not result.get("success") and result.get("message"):
        st.error(result["message"])

    payload = result.get("unified_decision_payload") or {}
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    user_facing = payload.get("user_facing") if isinstance(payload.get("user_facing"), dict) else {}
    references = payload.get("references") if isinstance(payload.get("references"), dict) else {}
    trace = payload.get("trace") if isinstance(payload.get("trace"), dict) else {}

    # 无 payload 时从 raw unified_decision 兜底
    if not payload and isinstance(result.get("unified_decision"), dict):
        ud = result["unified_decision"]
        status = {
            "overall_recommendation": ud.get("overall_recommendation"),
            "decision_confidence": ud.get("decision_confidence"),
            "confidence_reason": ud.get("confidence_reason"),
        }
        decision = {
            "final_summary": ud.get("final_summary"),
            "decision_focus": ud.get("decision_focus"),
            "final_action": ud.get("final_action"),
            "house_signal": ud.get("house_signal"),
            "risk_signal": ud.get("risk_signal"),
        }
        analysis = {
            "supporting_reasons": ud.get("supporting_reasons") or [],
            "primary_blockers": ud.get("primary_blockers") or [],
            "missing_information": ud.get("missing_information") or [],
        }
        user_facing = {
            "summary": ud.get("user_facing_summary"),
            "reason": ud.get("user_facing_reason") or [],
            "risk_note": ud.get("user_facing_risk_note") or [],
            "next_step": ud.get("user_facing_next_step") or [],
            "explanation": ud.get("user_facing_explanation") or [],
        }
        references = {
            "house_reference": ud.get("house_reference") or {},
            "risk_reference": ud.get("risk_reference") or {},
        }
        trace = {
            "trace_summary": ud.get("trace_summary"),
            "decision_trace": ud.get("decision_trace") or [],
            "blocker_trace": ud.get("blocker_trace") or [],
        }

    ok = bool(result.get("success"))

    st.markdown("## %s" % lab["criteria_section"])
    _norm_single = normalize_form_values(raw_form)
    render_criteria_summary(
        summarize_analyze_context(_norm_single),
        empty_caption=lab["criteria_empty"],
    )
    st.divider()

    # ========== Phase6 结果顺序：Overview → Property score → Decision → 四块解释 → 补充区 → References → 占位风险 → Debug ==========
    st.markdown(f"## {lab['overview']}")
    with st.container():
        col_o1, col_o2 = st.columns([1, 2])
        with col_o1:
            st.markdown("**Run status**")
            if err_msg:
                st.error(lab["run_status_failed"])
            elif ok:
                st.success(lab["run_status_ok"])
            else:
                st.warning(lab["run_status_partial"])
            st.caption(f"Engine success flag: `{ok}`")
        with col_o2:
            msg = result.get("message") or ""
            st.markdown("**Engine message**")
            st.write(_display_text(msg, "N/A") if msg or err_msg else "N/A")
            one_line = safe_get(user_facing, "summary") if isinstance(user_facing, dict) else "N/A"
            if one_line == "N/A":
                one_line = _display_text(decision.get("final_summary") if decision else None, "N/A")
            st.markdown("**At a glance**")
            st.write(one_line)

    st.divider()
    st.markdown("## %s" % lab["listing_snapshot"])
    st.caption(lab["listing_snapshot_caption"])
    _ctx = normalize_form_values(raw_form)
    render_listing_result_card(
        build_analyze_card_model(result, listing_context=_ctx),
        detail_bundle=build_analyze_detail_bundle(result, _ctx),
        detail_expander_key="p4_detail_analyze",
    )

    st.divider()

    st.markdown(f"## {lab['score']}")
    st.caption("Standard field `data.score` (mapped from engine final / property score).")
    with st.container():
        score = result.get("property_score")
        if score is not None:
            try:
                st.metric(label=lab["score"], value="%.2f" % float(score))
            except (TypeError, ValueError):
                st.metric(label=lab["score"], value=_display_text(score, "N/A"))
        else:
            st.info(lab["score_missing_hint"])

    st.divider()

    st.markdown(f"## {lab['decision']}")
    st.caption(lab["decision_caption"])
    with st.container():
        st.markdown("**Overall recommendation**")
        rec_val = safe_get(status, "overall_recommendation") if status else "N/A"
        st.write(rec_val)
        st.markdown("**Decision confidence**")
        st.write(_display_text(safe_get(status, "decision_confidence"), "N/A"))
        st.markdown("**Why this confidence level**")
        st.write(_display_text(safe_get(status, "confidence_reason"), "N/A"))
        st.markdown("---")
        st.markdown("**Decision detail**")
        format_decision_block(decision)

    st.divider()

    render_explanation_highlights(
        decision, analysis, user_facing, trace, references, result
    )

    st.divider()

    st.markdown(f"## {lab['analysis_detail']}")
    with st.container():
        format_analysis_block(analysis)

    st.divider()

    st.markdown(f"## {lab['user_facing']}")
    with st.container():
        format_user_facing_block(user_facing)

    st.divider()

    st.markdown(f"## {lab['references']}")
    with st.container():
        format_references_block(references)

    st.divider()

    st.markdown(f"## {lab['contract_risk']}")
    st.caption("Contract / clause risk module — placeholder in P1 Web UI.")
    with st.container():
        risk = result.get("risk_result") or {}
        st.info(_display_text(risk.get("message"), "No contract risk input for this demo."))

    # 调试区：默认折叠 + 弱 caption，避免抢主流程视觉
    with st.expander(lab["debug_expander"], expanded=False):
        st.caption("For developers only — not required for the demo walkthrough.")
        format_trace_block(trace, compact=True)
        st.markdown("**Engine explanation snapshot**")
        expl = result.get("explanation_summary") or {}
        if expl:
            st.write(_display_text(expl.get("summary"), "N/A"))
            pos = expl.get("key_positives") or expl.get("top_positive_reasons") or []
            neg = expl.get("key_risks") or expl.get("top_risk_reasons") or []
            if pos:
                st.markdown("**Positives (engine)**")
                for p in pos[:5]:
                    st.markdown(f"- {_display_text(p)}")
            if neg:
                st.markdown("**Risks (engine)**")
                for n in neg[:5]:
                    st.markdown(f"- {_display_text(n)}")
        else:
            st.caption("No data")
        st.markdown("**Final recommendation (raw JSON)**")
        frec = result.get("final_recommendation") or {}
        if frec:
            st.json(frec)
        else:
            st.caption("Empty")
        st.markdown("**Bridge payload (debug)**")
        st.json({k: v for k, v in result.items() if k != "explanation"})

    # P5 Phase5：单条 analyze 之后 — Agent summary + Refine（在完整结果之后）
    st.divider()
    _intent_s = resolve_intent_for_insights(st.session_state, normalized_form=_norm_single)
    _bundle_s = build_agent_insight_bundle(
        _intent_s,
        mode="single",
        single_result=result,
        batch_data=None,
    )
    render_agent_insight_panel(
        st,
        lab=lab,
        bundle=_bundle_s,
        intent=_intent_s,
        key_prefix="p5_insight_single",
    )

# --- P2 Phase4–5：批量接口 + 轻量结果展示区 ---
_DEFAULT_BATCH_JSON = """{
  "properties": [
    {"rent": 1200, "budget": 1500, "commute_minutes": 25, "bedrooms": 2, "bills_included": true},
    {"rent": 950, "budget": 1500, "commute_minutes": 40, "bedrooms": 1, "bills_included": false},
    {"rent": 1400, "budget": 1500, "commute_minutes": 15, "bedrooms": 2, "bills_included": true}
  ]
}"""
with st.expander(lab["batch_section_expander"], expanded=False):
    st.caption(lab.get("p7_real_batch_intro", ""))
    _real_btn_label = (
        lab.get("p7_real_batch_button", "Run real multi-source analysis")
        + (" (async)" if _p7_async else "")
    )
    if st.button(
        _real_btn_label,
        key="p7_real_batch",
        help=lab.get("p7_real_batch_help", ""),
    ):
        _intent_d = st.session_state.get("p5_agent_last_intent")
        _intent_o = (
            AgentRentalRequest.from_dict(_intent_d) if isinstance(_intent_d, dict) else None
        )
        _raw_f = collect_raw_form_from_session()

        if _p7_async:
            # ---- Async pilot path: POST /tasks + poll ----
            _status_box = st.empty()
            _status_box.info("Submitting async task to backend…")

            def _on_status(tid: str, status_text: str) -> None:
                _status_box.info("Task **%s** — %s" % (tid, status_text))

            try:
                _env, _terr, _req = run_real_listings_analysis_async(
                    api_base_url=_api_base,
                    intent=_intent_o,
                    form_raw=_raw_f,
                    limit_per_source=_p7_lim,
                    headless=_p7_h,
                    persist=_p7_persist,
                    on_status=_on_status,
                    auth_token=_auth_token,
                )
            except Exception as _ex:  # noqa: BLE001
                st.session_state["p2_batch_last"] = {
                    "success": False,
                    "error": {"message": str(_ex)},
                }
                st.session_state["p2_batch_last_request"] = {"properties": []}
            else:
                st.session_state["p2_batch_last"] = _env
                st.session_state["p2_batch_last_request"] = _req
                if isinstance(_req, dict) and _req.get("_p7_debug"):
                    st.session_state["p7_last_debug"] = _req["_p7_debug"]
                if _terr and isinstance(_req, dict):
                    _req.setdefault("_p7_transport_note", _terr)
            st.rerun()
        else:
            # ---- Original sync path (unchanged) ----
            try:
                with st.spinner(lab.get("p7_real_spinner", "Running…")):
                    _env, _terr, _req = run_real_listings_analysis(
                        intent=_intent_o,
                        form_raw=_raw_f,
                        limit_per_source=_p7_lim,
                        headless=_p7_h,
                        persist=_p7_persist,
                    )
            except Exception as _ex:  # noqa: BLE001
                st.session_state["p2_batch_last"] = {
                    "success": False,
                    "error": {"message": str(_ex)},
                }
                st.session_state["p2_batch_last_request"] = {"properties": []}
            else:
                st.session_state["p2_batch_last"] = _env
                st.session_state["p2_batch_last_request"] = _req
                if isinstance(_req, dict) and _req.get("_p7_debug"):
                    st.session_state["p7_last_debug"] = _req["_p7_debug"]
                if _terr and isinstance(_req, dict):
                    _req.setdefault("_p7_transport_note", _terr)
            st.rerun()

    st.caption(lab["batch_section_caption"])
    _dbg = st.session_state.get("p7_last_debug")
    if isinstance(_dbg, dict):
        try:
            st.caption(
                lab.get("p7_debug_caption", "")
                % (
                    ", ".join(_dbg.get("sources_run") or []) or "—",
                    str(_dbg.get("total_raw_count", "—")),
                    str(_dbg.get("aggregated_unique_count", "—")),
                    str(_dbg.get("total_analyzed_count", "—")),
                    float(_dbg.get("seconds") or 0),
                )
            )
        except (TypeError, ValueError):
            pass
    _batch_ta = st.text_area("Request JSON", value=_DEFAULT_BATCH_JSON, height=220, key="p2_batch_json")
    if st.button("Run batch request", key="p2_batch_run"):
        if _use_local:
            st.warning("Turn off **Use local engine** and ensure the API is running to test `/analyze-batch`.")
        else:
            import json

            import requests

            try:
                _payload = json.loads(_batch_ta)
            except json.JSONDecodeError as ex:
                st.error("Invalid JSON: %s" % ex)
            else:
                try:
                    _bu = _api_base.rstrip("/")
                    _batch_url = "%s/analyze-batch" % _bu
                    with st.spinner(lab["spinner_batch"]):
                        _headers = {"Authorization": "Bearer %s" % _auth_token} if _auth_token else None
                        _br = requests.post(_batch_url, json=_payload, timeout=180, headers=_headers)
                        _br.raise_for_status()
                        _bj = _br.json()
                    _ui_api_failures.record_success("/analyze-batch")
                    st.session_state["p2_batch_last"] = _bj
                    st.session_state["p2_batch_last_request"] = _payload
                    with st.expander("Raw JSON response", expanded=False):
                        st.json(_bj)
                except Exception as ex:
                    _ui_logger.error("Batch request failed | url=%s | error=%s", _batch_url, ex)
                    _ui_api_failures.record_failure("/analyze-batch", str(ex))
                    st.error(_display_text(str(ex), "Request failed"))

    _last_batch = st.session_state.get("p2_batch_last")
    if isinstance(_last_batch, dict):
        if not _last_batch.get("success"):
            _berr = _last_batch.get("error")
            _bmsg = ""
            if isinstance(_berr, dict):
                _bmsg = _display_text(_berr.get("message"), "")
            if _bmsg:
                st.warning(lab["batch_last_failed"] % _bmsg)
        elif isinstance(_last_batch.get("data"), dict):
            _bd = _last_batch["data"]
            st.divider()
            section_header(st, lab["batch_results_header"], level=3)
            st.markdown("**%s**" % lab["batch_criteria_title"])
            render_criteria_summary(
                summarize_batch_request(st.session_state.get("p2_batch_last_request")),
                empty_caption=lab["criteria_empty"],
            )
            st.markdown("**%s**" % lab["batch_comparison_title"])
            st.text(_bd.get("comparison_summary") or "N/A")
            _rs = _bd.get("risk_summary")
            if isinstance(_rs, dict):
                st.markdown("**%s**" % lab["batch_risk_summary_title"])
                st.caption(_rs.get("summary_text") or "N/A")
            with st.expander(lab["p4_batch_ranking_expander"], expanded=False):
                st.dataframe(_bd.get("ranking") or [], use_container_width=True, hide_index=True)

            _rows = _bd.get("results")
            _displayed: list = []
            _rows_raw: list = []
            section_header(st, lab["p4_filter_sort_title"], level=4)
            if not isinstance(_rows, list) or len(_rows) == 0:
                st.info(lab["batch_no_rows"])
            else:
                _rows_raw = [r for r in _rows if isinstance(r, dict)]
                _top_set = collect_top_indices(_bd)
                _src_choices = ["all"] + collect_source_values(_rows_raw)
                _rec_labels = {
                    "all": "All",
                    "top_only": "Top only",
                    "recommended_only": "Recommended only",
                    "review_only": "Review only",
                }
                _bills_labels = {"all": "All", "included_only": "Bills included only"}
                _fur_labels = {"all": "All", "furnished_only": "Furnished only"}
                _ptype_labels = {
                    "all": "All",
                    "flat": "Flat",
                    "house": "House",
                    "studio": "Studio",
                    "room": "Room",
                }
                _sort_labels = {
                    "score_desc": "Score (high → low)",
                    "rent_asc": "Rent (low → high)",
                    "rent_desc": "Rent (high → low)",
                    "bedrooms_desc": "Bedrooms (high → low)",
                    "title_asc": "Title (A–Z)",
                    "postcode_asc": "Postcode (A–Z)",
                }
                _r1, _r2, _r3 = st.columns(3)
                with _r1:
                    _fv_rec = st.selectbox(
                        "Recommendation",
                        options=list(_rec_labels.keys()),
                        format_func=lambda k: _rec_labels[k],
                        key="p4_batch_filter_rec",
                    )
                with _r2:
                    _fv_bills = st.selectbox(
                        "Bills",
                        options=list(_bills_labels.keys()),
                        format_func=lambda k: _bills_labels[k],
                        key="p4_batch_filter_bills",
                    )
                with _r3:
                    _fv_fur = st.selectbox(
                        "Furnished",
                        options=list(_fur_labels.keys()),
                        format_func=lambda k: _fur_labels[k],
                        key="p4_batch_filter_furnished",
                    )
                _r4, _r5, _r6 = st.columns(3)
                with _r4:
                    _fv_pt = st.selectbox(
                        "Property type",
                        options=list(_ptype_labels.keys()),
                        format_func=lambda k: _ptype_labels[k],
                        key="p4_batch_filter_ptype",
                    )
                with _r5:
                    _fv_src = st.selectbox(
                        "Source",
                        options=_src_choices,
                        format_func=lambda k: k if k != "all" else "All",
                        key="p4_batch_filter_source",
                    )
                with _r6:
                    _fv_sort = st.selectbox(
                        "Sort by",
                        options=list(_sort_labels.keys()),
                        format_func=lambda k: _sort_labels[k],
                        key="p4_batch_sort",
                    )

                _filtered = filter_batch_rows(
                    _rows_raw,
                    recommendation=_fv_rec,
                    top_indices=_top_set,
                    bills=_fv_bills,
                    furnished=_fv_fur,
                    property_type=_fv_pt,
                    source=_fv_src,
                )
                _displayed = sort_batch_rows(_filtered, _fv_sort)

            st.divider()
            section_header(st, lab["p4_batch_results_by_tier"], level=4)
            if not _rows_raw:
                st.caption(lab["batch_tier_prereq"])
            elif len(_displayed) == 0:
                st.warning(lab["p4_no_matches"])
            else:
                render_batch_partitioned_listings(
                    st,
                    lab=lab,
                    batch_data=_bd,
                    rows_raw=_rows_raw,
                    displayed=_displayed,
                    debug_display_text_fn=_display_text,
                    detail_key_prefix="p4_detail_batch",
                )

                st.divider()
                section_header(st, "P10 · 推荐理由 (Explain Engine)", level=4)
                st.caption("规则驱动（无大模型）：基于各维度得分与表单信息生成摘要、优缺点与风险提示。")
                if len(_displayed) == 0:
                    st.caption("当前筛选下无行，无法展示 explain。")
                else:
                    for _r in _displayed:
                        if not isinstance(_r, dict):
                            continue
                        _pex = build_p10_explain_for_batch_row(_r)
                        _sum_preview = (_pex.get("explain_summary") or "")[:72]
                        with st.expander(
                            "Listing %s — %s" % (_r.get("index", "?"), _sum_preview or "—"),
                            expanded=False,
                        ):
                            st.markdown("**摘要**")
                            st.info(_pex.get("explain_summary") or "—")
                            st.markdown("**优点**")
                            _pros = _pex.get("pros") or []
                            if _pros:
                                for _pr in _pros:
                                    st.markdown("- %s" % _pr)
                            else:
                                st.caption("（无）")
                            st.markdown("**缺点**")
                            _cons = _pex.get("cons") or []
                            if _cons:
                                for _cn in _cons:
                                    st.markdown("- %s" % _cn)
                            else:
                                st.caption("（无）")
                            st.markdown("**风险提示**")
                            _rfs = _pex.get("risk_flags") or []
                            if _rfs:
                                for _rf in _rfs:
                                    st.warning(_rf)
                            else:
                                st.caption("（无）")

                st.divider()
                section_header(st, "P10 · Favorites & compare (this batch)", level=4)
                if not _auth_token:
                    st.caption("Sidebar: login to save favorites and run **POST /compare** on two listings.")
                elif len(_displayed) == 0:
                    st.caption("No rows in the current filter — adjust filters to compare or favorite.")
                else:
                    import requests as _req_p10b

                    _bu_b = _api_base.rstrip("/")
                    _h_b = {"Authorization": "Bearer %s" % _auth_token}
                    _row_list = [r for r in _displayed if isinstance(r, dict)]
                    _labels_b = [batch_row_compare_label(r) for r in _row_list]
                    _pick_b = st.multiselect(
                        "Select one or more listings → **Add to favorites**",
                        options=_labels_b,
                        key="p10_batch_fav_pick",
                    )
                    if st.button("Add selected to favorites", key="p10_batch_fav_btn"):
                        _msgs: list[str] = []
                        for _lab in _pick_b:
                            _ix = _labels_b.index(_lab)
                            _body = batch_row_to_favorite_payload(_row_list[_ix])
                            try:
                                _fr = _req_p10b.post(
                                    "%s/favorites" % _bu_b,
                                    json=_body,
                                    headers=_h_b,
                                    timeout=25,
                                )
                                if _fr.status_code >= 400:
                                    try:
                                        _ej = _fr.json()
                                        _em = _ej.get("error", _fr.text)
                                    except Exception:
                                        _em = _fr.text
                                    _msgs.append("%s: %s" % (_lab[:40], _em))
                                else:
                                    _msgs.append("%s: saved" % _lab[:40])
                            except Exception as _ex_b:  # noqa: BLE001
                                _msgs.append(str(_ex_b))
                        st.caption(" | ".join(_msgs[:6]))
                    _c_a, _c_b = st.columns(2)
                    with _c_a:
                        _cmp_a = st.selectbox("Compare A", _labels_b, key="p10_cmp_a_sel")
                    with _c_b:
                        _cmp_b = st.selectbox("Compare B", _labels_b, key="p10_cmp_b_sel")
                    if st.button("Run compare (POST /compare)", key="p10_cmp_run_btn"):
                        if _cmp_a == _cmp_b:
                            st.warning("Pick two different listings.")
                        else:
                            _ia = _labels_b.index(_cmp_a)
                            _ib = _labels_b.index(_cmp_b)
                            try:
                                _cr = _req_p10b.post(
                                    "%s/compare" % _bu_b,
                                    json={"properties": [_row_list[_ia], _row_list[_ib]]},
                                    headers=_h_b,
                                    timeout=30,
                                )
                                _cr.raise_for_status()
                                st.session_state["p10_compare_last"] = _cr.json()
                            except Exception as _ex_b:  # noqa: BLE001
                                st.session_state["p10_compare_last"] = {"error": str(_ex_b)}
                    _last_cmp = st.session_state.get("p10_compare_last")
                    if _last_cmp:
                        _cmpd = _last_cmp.get("comparison") if isinstance(_last_cmp, dict) else None
                        if isinstance(_cmpd, dict):
                            _items_cmp = _cmpd.get("items") or []
                            with st.expander("Compare — explain 摘要 (P10)", expanded=True):
                                for _it in _items_cmp:
                                    if not isinstance(_it, dict):
                                        continue
                                    _exi = _it.get("explain") or {}
                                    st.markdown(
                                        "**Listing %s** — %s"
                                        % (
                                            _it.get("batch_index"),
                                            _exi.get("explain_summary") or "—",
                                        )
                                    )
                                    if _exi.get("pros"):
                                        st.caption("优点: " + " · ".join(_exi.get("pros") or []))
                                    if _exi.get("cons"):
                                        st.caption("缺点: " + " · ".join(_exi.get("cons") or []))
                                    st.divider()
                        with st.expander("Last compare result (full JSON)", expanded=False):
                            st.json(_last_cmp)

            # P5 Phase5：batch 列表与筛选之后 — Agent summary + Refine
            st.divider()
            _intent_b = resolve_intent_for_insights(
                st.session_state,
                batch_request=st.session_state.get("p2_batch_last_request"),
            )
            _bundle_b = build_agent_insight_bundle(
                _intent_b,
                mode="batch",
                single_result=None,
                batch_data=_bd,
            )
            render_agent_insight_panel(
                st,
                lab=lab,
                bundle=_bundle_b,
                intent=_intent_b,
                key_prefix="p5_insight_batch",
            )

render_demo_footer()
