# P1 Phase1: Web UI 桥接层 - 把表单输入转成 Engine 可接受格式并返回展示用结果
# 不重构原引擎，只做一层包装

import sys
import io

from state import init_state
from scoring_adapter import generate_ranking_api_response

# P1 Phase2: 表单默认值（数字留空时使用）
_WEB_FORM_DEFAULTS = {
    "rent": 1200.0,
    "budget": 1500.0,
    "commute_minutes": 30,
    "bedrooms": 2,
}


def normalize_web_form_inputs(raw: dict) -> dict:
    """
    P1 Phase2: 将页面表单原始值规范为 run_web_demo_analysis 所需格式。
    P1 Phase5: Web 端已在提交前做必填与数值校验；此处仍保留空值默认与容错，供脚本或其它入口复用。
    - 空字符串 / None → 使用默认值（rent/budget/commute/bedrooms）
    - bills_included: 支持 bool 或 str
    - distance: 可空，无效则 None
    """
    if not raw or not isinstance(raw, dict):
        raw = {}

    def _float(key: str, default_key: str) -> float | None:
        v = raw.get(key)
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return float(_WEB_FORM_DEFAULTS[default_key])
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(_WEB_FORM_DEFAULTS[default_key])

    def _int(key: str, default_key: str) -> int | None:
        v = raw.get(key)
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return int(_WEB_FORM_DEFAULTS[default_key])
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return int(_WEB_FORM_DEFAULTS[default_key])

    bills = raw.get("bills_included")
    if isinstance(bills, str):
        bills = str(bills).strip().lower() in ("yes", "y", "true", "1", "包", "包含")
    elif bills is None:
        bills = False

    dist = raw.get("distance")
    distance_out = None
    if dist is not None and str(dist).strip() != "":
        try:
            distance_out = float(dist)
        except (TypeError, ValueError):
            distance_out = None

    return {
        "rent": _float("rent", "rent"),
        "budget": _float("budget", "budget"),
        "commute_minutes": _int("commute_minutes", "commute_minutes"),
        "bedrooms": _int("bedrooms", "bedrooms"),
        "bills_included": bool(bills),
        "area": (raw.get("area") or "").strip() or None,
        "postcode": (raw.get("postcode") or "").strip() or None,
        "target_postcode": (raw.get("target_postcode") or "").strip() or None,
        "distance": distance_out,
    }


def run_web_demo_analysis(input_data: dict) -> dict:
    """
    把 Web 表单输入转成 Engine 能接受的格式，调用分析，返回稳定 dict 给页面展示。

    输入 input_data 建议字段:
      - rent: 月租 (int/float)
      - bills_included: 是否包 bill (bool/str: yes/no)
      - commute_minutes: 通勤分钟 (int)
      - area: 区域名 (str)
      - postcode: 邮编 (str)
      - bedrooms: 卧室数 (int)
      - budget: 预算 (int, 默认 1500)
      - target_postcode: 目标邮编 (str, 可选)
      - distance: 距离 (float, 可选，英里等，与 module2 distance 一致)

    返回 dict 含:
      - success: bool
      - message: str
      - property_score: float | None
      - explanation_summary: dict
      - final_recommendation: dict
      - unified_decision: dict
      - unified_decision_payload: dict
      - risk_result: dict (占位)
    """
    out = {
        "success": False,
        "message": "",
        "property_score": None,
        "explanation_summary": {},
        "final_recommendation": {},
        "unified_decision": {},
        "unified_decision_payload": {},
        "risk_result": {"status": "placeholder", "message": "暂未输入合同风险信息"},
        "top_house_export": {},
    }
    try:
        house = _input_to_house(input_data)
        if not house:
            out["message"] = "请至少填写租金 (rent) 或基础信息"
            return out

        state = init_state()
        state["listings"] = [house]
        state["settings"]["budget"] = input_data.get("budget") or 1500

        # 临时抑制 print 输出，避免 Windows gbk 编码下 emoji 报错
        _old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            api_resp = generate_ranking_api_response(state)
        finally:
            sys.stdout = _old_stdout
        data = api_resp.get("data") or {}

        out["success"] = api_resp.get("success", False)
        out["message"] = api_resp.get("message", "")

        houses = data.get("houses") or []
        if houses:
            h0 = houses[0]
            out["property_score"] = h0.get("final_score")
            out["explanation_summary"] = h0.get("explanation_summary") or {}
            out["explanation"] = h0.get("explanation") or {}
            # P2 Phase3: 供 /score-breakdown 等子接口复用（标准 houses[0] 契约子集）
            out["top_house_export"] = {
                "rank": h0.get("rank"),
                "house_label": h0.get("house_label"),
                "final_score": h0.get("final_score"),
                "scores": h0.get("scores") if isinstance(h0.get("scores"), dict) else {},
                "reasons": h0.get("reasons") if isinstance(h0.get("reasons"), dict) else {},
                "explain": h0.get("explain") if isinstance(h0.get("explain"), dict) else {},
            }

        out["final_recommendation"] = data.get("final_recommendation") or {}
        out["unified_decision"] = data.get("unified_decision") or {}
        out["unified_decision_payload"] = data.get("unified_decision_payload") or {}
        out["top_house_summary"] = data.get("top_house_summary") or {}
        out["summary"] = data.get("summary") or {}

    except Exception as e:
        out["message"] = "分析出错: %s" % str(e)
    return out


def _input_to_house(d: dict) -> dict | None:
    """把 Web 表单字段转成 module2 rank_houses 能接受的 house 结构。"""
    if not d or not isinstance(d, dict):
        return None
    rent = d.get("rent")
    if rent is not None:
        try:
            rent = float(rent)
        except (TypeError, ValueError):
            rent = None
    if rent is None and not any(d.get(k) for k in ("area", "postcode", "commute_minutes", "bedrooms", "distance")):
        return None

    bills = d.get("bills_included")
    if isinstance(bills, str):
        bills = str(bills).strip().lower() in ("yes", "y", "true", "1", "包", "包含")
    elif bills is None:
        bills = False

    commute = d.get("commute_minutes")
    if commute is not None:
        try:
            commute = int(float(commute))
        except (TypeError, ValueError):
            commute = None

    bedrooms = d.get("bedrooms")
    if bedrooms is not None:
        try:
            bedrooms = int(float(bedrooms))
        except (TypeError, ValueError):
            bedrooms = None

    area = (d.get("area") or "").strip() or None
    postcode = (d.get("postcode") or "").strip() or None
    distance = d.get("distance")
    if distance is not None:
        try:
            distance = float(distance)
        except (TypeError, ValueError):
            distance = None

    house = {
        "rent": rent,
        "bills": "included" if bills else "excluded",
        "commute_mins": commute,
        "area": area,
        "postcode": postcode,
        "bedrooms": bedrooms,
        "distance": distance,
    }
    return house


def listing_dict_to_engine_house(
    listing_dict: dict,
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> dict | None:
    """
    标准 listing dict → module2 rank_houses 使用的 house（多房源排序 / AI 桥接）。
    Phase A1：先经 house_canonical 统一字段，再 normalize_listing_payload + to_analyze_payload + _input_to_house。
    """
    from data.normalizer.listing_normalizer import normalize_listing_payload, to_analyze_payload
    from house_canonical import canonical_to_listing_row, normalize_house_record

    if not isinstance(listing_dict, dict):
        return None
    try:
        src = str(listing_dict.get("source") or "unknown")
        row = canonical_to_listing_row(normalize_house_record(listing_dict, source=src))
        ls = normalize_listing_payload(row, source=row.get("source"))
        payload = to_analyze_payload(ls, budget=budget, target_postcode=target_postcode)
        normalized = normalize_web_form_inputs(payload)
        return _input_to_house(normalized)
    except Exception:
        return None


if __name__ == "__main__":
    result = run_web_demo_analysis({
        "rent": 1200,
        "bills_included": True,
        "commute_minutes": 25,
        "bedrooms": 2,
        "budget": 1500
    })

    print("SUCCESS:", result.get("success"))
    print("SCORE:", result.get("property_score"))
    print("TOP KEYS:", list(result.get("unified_decision_payload", {}).keys()))
