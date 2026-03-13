from contract_risk import calculate_contract_risk_score


def run_case(title: str, text: str | None):
    print("\n" + "=" * 60)
    print(f"[CASE] {title}")
    print("- text:", repr(text))
    r = calculate_contract_risk_score(text)
    print("- risk_score:", r["risk_score"])
    print("- matched_categories:", r["matched_categories"])
    print("- matched_keywords:", r["matched_keywords"])
    print("- risk_reasons:")
    for line in r["risk_reasons"]:
        print("  -", line)


def main():
    # 1) 正常低风险文本
    run_case(
        "Low risk / normal",
        "Nice 1 bed flat. Viewing available. Standard tenancy agreement. Deposit protected.",
    )

    # 2) deposit risk 文本
    run_case(
        "Deposit risk",
        "Holding deposit non refundable. Deposit before viewing is required.",
    )

    # 3) scam risk 文本
    run_case(
        "Scam risk",
        "Urgent payment needed. Bank transfer only. No viewing. Send money now.",
    )

    # 4) 多风险叠加文本
    run_case(
        "Multi risks (deposit + scam + pressure + no contract)",
        "Decide today! Pay now. Cash only. Deposit before viewing. No contract, verbal only. No viewing.",
    )


if __name__ == "__main__":
    main()

