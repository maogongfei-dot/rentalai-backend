/** Mock contract risk detection results — frontend only, no API */
export const mockContractRisks = [
  {
    id: "risk-001",
    clause_title: "Break clause & early termination",
    risk_level: "high",
    issue: "Tenant break option is unclear and landlord notice period is very short.",
    explanation:
      "The agreement does not clearly state how much notice you must give to end the tenancy early, while the landlord can terminate with only 4 weeks' notice in some cases.",
    suggested_action:
      "Ask for a mutual break clause with equal notice periods (e.g. 2 months) and written confirmation.",
  },
  {
    id: "risk-002",
    clause_title: "Deposit deductions",
    risk_level: "medium",
    issue: "Cleaning and minor wear charges may be deducted without itemised evidence.",
    explanation:
      "The contract allows deductions for 'professional cleaning' and 'making good' without requiring receipts or a check-in/check-out inventory comparison.",
    suggested_action:
      "Request an inventory report at move-in and cap cleaning charges to reasonable costs with proof.",
  },
  {
    id: "risk-003",
    clause_title: "Rent increase clause",
    risk_level: "low",
    issue: "Annual rent review is mentioned but the calculation method is vague.",
    explanation:
      "The landlord may increase rent once per year, but the document does not specify whether increases follow a fixed percentage or an external index.",
    suggested_action:
      "Clarify that any increase must follow a stated formula and require at least one month's written notice.",
  },
];
