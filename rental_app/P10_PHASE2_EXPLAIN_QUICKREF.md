# P10 Phase2 Explain Quick Reference

---

## Summary

- 字段名：`explain_summary`  
- 一句话概括优缺点与综合分档位（中文，规则生成）。

---

## Pros

- 字段名：`pros`（JSON 数组）  
- 维度分 **≥ 80** 时生成对应优点短句（最多 3 条）。

---

## Cons

- 字段名：`cons`（JSON 数组）  
- 维度分 **≤ 50** 时生成对应缺点短句（最多 3 条）。

---

## Risk Flags

- 字段名：`risk_flags`（JSON 数组）  
- 来自 **账单是否包含**、**区域分**、**价格/通勤弱**、**decision_code** 等规则（最多 5 条）。

---

## Notes

- 当前为 **规则驱动 explain**，不调用大模型。  
- 维度与阈值对齐 **`module2_scoring`**（80 / 50）。  
- 实现模块：`data/explain/rule_explain.py`。
