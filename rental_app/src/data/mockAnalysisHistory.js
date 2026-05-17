/** Mock analysis history for Tenant Dashboard (frontend only, no API). */

export const MOCK_ANALYSIS_HISTORY = [
  {
    id: "ah-001",
    property_title: "Bright 2-bed flat near Angel",
    location: "Islington, London N1",
    analysis_type: "Property & Risk Analysis",
    final_score: 82,
    risk_level: "Low",
    created_at: "2026-05-10T14:30:00.000Z",
    summary:
      "Strong location and fair rent for the area. Deposit terms look standard; minor commute trade-off noted.",
  },
  {
    id: "ah-002",
    property_title: "Modern studio with canal view",
    location: "Hackney, London E8",
    analysis_type: "Contract Review",
    final_score: 71,
    risk_level: "Medium",
    created_at: "2026-05-03T09:15:00.000Z",
    summary:
      "Bills included improves affordability. Watch for break-clause wording and early exit fees in section 4.",
  },
  {
    id: "ah-003",
    property_title: "Spacious 3-bed family home",
    location: "Walthamstow, London E17",
    analysis_type: "Full Rental Assessment",
    final_score: 88,
    risk_level: "Low",
    created_at: "2026-04-22T18:45:00.000Z",
    summary:
      "Excellent space for the price. Low overall risk; verify council tax band and transport links for school runs.",
  },
];
