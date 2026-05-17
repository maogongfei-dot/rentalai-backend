/** Mock contract missing/weak clauses — frontend only, no API */
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
