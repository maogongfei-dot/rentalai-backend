"""
Module3 Phase1-A5: Input Type Detection.

识别用户输入属于哪一种类型：question / contract_clause / dispute.
用于 RentalAI 合同风险与纠纷分析前的输入分类。
"""

# 返回值仅限以下三种
INPUT_TYPE_QUESTION = "question"
INPUT_TYPE_CONTRACT_CLAUSE = "contract_clause"
INPUT_TYPE_DISPUTE = "dispute"

# 问句特征：句首词（小写）
QUESTION_STARTERS = (
    "can", "should", "is", "do", "does", "what", "why", "when", "how"
)

# 合同条款关键词（出现多个时倾向判定为 contract_clause）
CONTRACT_KEYWORDS = (
    "tenant", "landlord", "shall", "must", "agreement", "clause", "rent", "deposit"
)

# 纠纷描述关键词（出现任一则倾向判定为 dispute）
DISPUTE_KEYWORDS = (
    "refuse", "not return", "issue", "dispute", "complain", "illegal", "charged"
)

# 判定优先级：dispute > contract_clause > question


def detect_input_type(text: str) -> str:
    """
    根据简单规则判断输入类型。

    规则优先级：dispute > contract_clause > question。
    - question: 文本含 '?' 或以问句常用词开头（can/should/is/do/does/what/why/when/how）。
    - contract_clause: 文本包含多个合同关键词（tenant, landlord, shall, must, agreement, clause, rent, deposit）。
    - dispute: 文本包含纠纷关键词（refuse, not return, issue, dispute, complain, illegal, charged）。

    :param text: 用户输入文本
    :return: "question" | "contract_clause" | "dispute"
    """
    if not text or not isinstance(text, str):
        return INPUT_TYPE_QUESTION

    raw = text.strip()
    if not raw:
        return INPUT_TYPE_QUESTION

    lower = raw.lower()

    # 1. 优先：纠纷关键词
    for kw in DISPUTE_KEYWORDS:
        if kw in lower:
            return INPUT_TYPE_DISPUTE

    # 2. 其次：多个合同关键词
    contract_count = sum(1 for kw in CONTRACT_KEYWORDS if kw in lower)
    if contract_count >= 2:
        return INPUT_TYPE_CONTRACT_CLAUSE

    # 3. 再次：问句特征（含 ? 或以问句词开头）
    if "?" in raw:
        return INPUT_TYPE_QUESTION
    first_word = lower.split()[0] if lower.split() else ""
    if first_word in QUESTION_STARTERS:
        return INPUT_TYPE_QUESTION

    # 默认：未明确匹配时视为一般问题
    return INPUT_TYPE_QUESTION


def _demo():
    """简单测试示例：打印三种典型输入的检测结果。"""
    examples = [
        "Can my landlord increase rent?",
        "The tenant must pay rent on the first day.",
        "My landlord refused to return my deposit.",
    ]
    print("--- Module3 Phase1-A5: Input Type Detection ---")
    for text in examples:
        result = detect_input_type(text)
        print(f"  {result!r}  <-  {text!r}")
    print("--- done ---")


if __name__ == "__main__":
    _demo()
