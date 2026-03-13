from contract_risk import calculate_structured_risk_score


def run_case(title: str, listing: dict | None):
    print("\n" + "=" * 60)
    print(f"[CASE] {title}")
    print("- listing:", listing)
    r = calculate_structured_risk_score(listing)
    print("- structured_risk_score:", r["structured_risk_score"])
    print("- matched_rules:", r["matched_rules"])
    print("- risk_reasons:")
    for line in r["risk_reasons"]:
        print("  -", line)


def main():
    # 1) 正常低风险 listing
    run_case(
        "Low risk / normal",
        {
            "rent": 1500,
            "deposit_amount": 1500,
            "viewing_available": True,
            "contract_available": True,
            "payment_method": "bank transfer",
            "notes": "Viewing available. Standard tenancy agreement.",
            "bills": True,
        },
    )

    # 2) deposit 风险 listing（押金过高 + holding deposit non-refundable）
    run_case(
        "Deposit risk",
        {
            "rent": "1200",
            "deposit_amount": "2200",
            "holding_deposit": "holding deposit non-refundable",
            "notes": "deposit required",
        },
    )

    # 3) no viewing + transfer only 高风险 listing
    run_case(
        "High risk: no viewing + transfer only",
        {
            "rent": 1400,
            "viewing_available": False,
            "payment_method": "bank transfer only",
            "description": "No viewing. Urgent payment needed. Bank transfer only. Pay now.",
        },
    )

    # 4) no contract + deposit + urgent payment 组合风险
    run_case(
        "High risk combo: no contract + deposit + urgent payment",
        {
            "rent": 1300,
            "deposit_amount": 2200,
            "contract_available": False,
            "notes": "No contract, verbal only. Cash only. Urgent payment, pay now.",
        },
    )


if __name__ == "__main__":
    main()

