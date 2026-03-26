"""
Phase C1：Query Parser v2 本地样例（中英混合），用于快速人工/脚本验证。
用法：python -m query_parser_samples
"""

from __future__ import annotations

import json

from rental_query_parser import parse_user_query

# 至少 10 条，覆盖 budget / bedrooms / city / bills / station / couple / safety / quiet / postcode
SAMPLE_QUERIES: list[str] = [
    "Milton Keynes 月租 1200 以内 一居室",
    "London bills included studio under 1400",
    "适合情侣 离车站近 预算 1500 左右 furnished",
    "Manchester 两居室 通勤方便 2 bed flat",
    "Birmingham B1 1AA 预算 between 1000 and 1300",
    "最低900，最高1200，包bill，安静一点",
    "Shoreditch area safer area low crime",
    "MK9 2AB 2 bedroom near station",
    "below 1500 pcm 3 bed house Liverpool",
    "around 1400 budget couple friendly easy commute",
    "包水电 精装带家具 一居室 London",
    "not ideal for couples shared house room in Camden NW1",
]


def run_samples() -> None:
    for q in SAMPLE_QUERIES:
        out = parse_user_query(q)
        print("---")
        print("Q:", q)
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_samples()
