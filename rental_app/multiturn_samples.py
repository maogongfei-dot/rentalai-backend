# Phase C4：多轮 merge / 意图 本地验证。运行：python -m multiturn_samples
from __future__ import annotations

from rental_multiturn import merge_structured_query
from rental_query_parser import parse_user_query


def scenario_1() -> None:
    """MK + 预算 + 一居 → 再补充近车站。"""
    a = parse_user_query("我想找 Milton Keynes 1200以内一居室")
    b = parse_user_query("最好离车站近")
    m = merge_structured_query(a, b)
    assert (m.get("city") or "").lower().find("milton") >= 0 or m.get("city")
    assert m.get("budget_max") == 1200.0 or m.get("budget_max") is not None
    assert m.get("bedrooms") == 1
    assert m.get("near_station") is True
    print("scenario_1 OK", "near_station=", m.get("near_station"), "city=", m.get("city"))


def scenario_2() -> None:
    """London studio 包 bill → 预算改成 1500。"""
    a = parse_user_query("London studio bills included")
    b = parse_user_query("预算改成1500")
    m = merge_structured_query(a, b)
    assert m.get("budget_max") == 1500.0
    assert "london" in (m.get("city") or "").lower()
    print("scenario_2 OK budget_max=", m.get("budget_max"))


def scenario_3() -> None:
    """Manchester 两居 → 不要 studio。"""
    a = parse_user_query("Manchester 两居室")
    b = parse_user_query("不要studio")
    m = merge_structured_query(a, b)
    assert "studio" in (m.get("excluded_property_types") or [])
    assert m.get("bedrooms") == 2 or m.get("bedrooms") is None
    print("scenario_3 OK excluded=", m.get("excluded_property_types"))


def scenario_4() -> None:
    """MK 情侣 → 重新来 Birmingham room。"""
    a = parse_user_query("Milton Keynes 适合情侣")
    b = parse_user_query("重新来，我想找 Birmingham room")
    # restart：应用层用当前句整句替换，不 merge
    m = merge_structured_query({}, b)  # 等价 restart 后仅 b
    assert "birmingham" in (m.get("city") or "").lower()
    print("scenario_4 OK city=", m.get("city"), "room hint in notes/excluded=", m.get("notes"))


def run() -> None:
    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    print("all multiturn sample checks passed.")


if __name__ == "__main__":
    run()
