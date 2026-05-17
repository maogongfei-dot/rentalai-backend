/** Contract Analysis Center — consolidated mock data (frontend only, no API) */

export const mockContractRisks = [
  {
    id: "risk-001",
    clause_title: "Break clause & early termination",
    risk_level: "high",
    issue:
      "Tenant break option is unclear and landlord notice period is very short.",
    explanation:
      "The agreement does not clearly state how much notice you must give to end the tenancy early, while the landlord can terminate with only 4 weeks' notice in some cases.",
    suggested_action:
      "Ask for a mutual break clause with equal notice periods (e.g. 2 months) and written confirmation.",
  },
  {
    id: "risk-002",
    clause_title: "Deposit deductions",
    risk_level: "medium",
    issue:
      "Cleaning and minor wear charges may be deducted without itemised evidence.",
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

export const mockMissingClauses = [
  {
    id: "missing-001",
    clause_name: "Inventory & condition report",
    status: "missing",
    importance: "high",
    explanation:
      "There is no schedule describing the property condition at the start of the tenancy.",
    suggested_fix:
      "Add an annexed inventory with photos, meter readings, and signatures from both parties within 7 days of move-in.",
  },
  {
    id: "missing-002",
    clause_name: "Repairs & maintenance response times",
    status: "weak",
    importance: "medium",
    explanation:
      "The contract mentions repairs but does not set clear deadlines for urgent vs non-urgent issues.",
    suggested_fix:
      "Specify response times (e.g. 24 hours for heating/water loss, 14 days for minor repairs) and a reporting channel.",
  },
  {
    id: "missing-003",
    clause_name: "Subletting & guest policy",
    status: "unclear",
    importance: "low",
    explanation:
      "Rules on guests staying overnight and informal subletting are not clearly defined.",
    suggested_fix:
      "Clarify maximum guest stay duration and require written consent before any sublet or licence arrangement.",
  },
];

export const mockContractChatExamples = {
  placeholder: "Ask a question about your tenancy agreement.",
  emptyMessage: "Ask a question about your tenancy agreement.",
  defaultReply:
    "This is a mock contract explanation. The full contract AI engine will be connected later.",
  examples: [
    {
      id: "chat-example-001",
      question: "Can my landlord increase rent during the fixed term?",
      answer:
        "This is a mock contract explanation. The full contract AI engine will be connected later.",
    },
    {
      id: "chat-example-002",
      question: "What notice do I need to give to end the tenancy early?",
      answer:
        "This is a mock contract explanation. The full contract AI engine will be connected later.",
    },
  ],
};

/**
 * Build Contract Summary cards from mock analysis inputs.
 * Replace with API response mapping when the real contract engine is connected.
 */
export function mockContractSummary({ selectedFile, risks, clauses }) {
  const highRisks = risks.filter((r) => r.risk_level === "high").length;
  const missingWeakCount = clauses.filter(
    (c) => c.status === "missing" || c.status === "weak",
  ).length;
  const reviewStatus = selectedFile ? "Ready for review" : "Awaiting upload";
  const reviewTone = selectedFile ? "ready" : "pending";

  return [
    {
      id: "uploaded-file",
      label: "Uploaded File",
      value: selectedFile ? selectedFile.name : "Not uploaded",
      detail: selectedFile
        ? "Tenancy agreement selected"
        : "Upload a PDF, DOC, or DOCX",
      tone: selectedFile ? "success" : "neutral",
    },
    {
      id: "detected-risks",
      label: "Detected Risks",
      value: String(risks.length),
      detail:
        risks.length === 0
          ? "No issues flagged"
          : `${highRisks} high · mock preview`,
      tone: highRisks > 0 ? "warning" : "neutral",
    },
    {
      id: "missing-clauses",
      label: "Missing / Weak Clauses",
      value: String(missingWeakCount),
      detail: `${clauses.length} items checked · mock preview`,
      tone: missingWeakCount > 0 ? "warning" : "success",
    },
    {
      id: "review-status",
      label: "Review Status",
      value: reviewStatus,
      detail: selectedFile
        ? "Mock analysis sections are active"
        : "Select a contract to begin",
      tone: reviewTone,
    },
  ];
}
