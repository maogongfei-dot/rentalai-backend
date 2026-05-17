/**
 * Tenant Center mock data (frontend only, no API).
 * Replace imports in TenantDashboard with real API responses when ready.
 */

export const MOCK_SAVED_PROPERTIES = [
  {
    id: "sp-001",
    title: "Bright 2-bed flat near Angel",
    location: "Islington, London N1",
    rent: 2150,
    bedrooms: 2,
    bills_included: false,
    risk_level: "Low",
    score: 82,
  },
  {
    id: "sp-002",
    title: "Modern studio with canal view",
    location: "Hackney, London E8",
    rent: 1450,
    bedrooms: 1,
    bills_included: true,
    risk_level: "Medium",
    score: 71,
  },
  {
    id: "sp-003",
    title: "Spacious 3-bed family home",
    location: "Walthamstow, London E17",
    rent: 1895,
    bedrooms: 3,
    bills_included: false,
    risk_level: "Low",
    score: 88,
  },
];

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

export const MOCK_COMPARE_PROPERTIES = [
  {
    id: "cp-001",
    title: "Bright 2-bed flat near Angel",
    rent: 2150,
    commute_score: 88,
    bills_score: 72,
    area_score: 91,
    risk_score: 85,
    final_score: 84,
  },
  {
    id: "cp-002",
    title: "Modern studio with canal view",
    rent: 1450,
    commute_score: 79,
    bills_score: 90,
    area_score: 76,
    risk_score: 74,
    final_score: 80,
  },
  {
    id: "cp-003",
    title: "Spacious 3-bed family home",
    rent: 1895,
    commute_score: 71,
    bills_score: 68,
    area_score: 89,
    risk_score: 88,
    final_score: 88,
  },
];

export const MOCK_BUDGET_INSIGHTS = {
  monthly_income: 3500,
  target_rent: 1450,
  estimated_bills: 180,
  estimated_transport: 120,
  estimated_food_cost: 350,
  affordability_score: 78,
  rent_pressure_level: "Low",
  estimated_remaining_balance: 1400,
};

/** Convenience bundle for future API adapter layer. */
export const tenantMockData = {
  savedProperties: MOCK_SAVED_PROPERTIES,
  analysisHistory: MOCK_ANALYSIS_HISTORY,
  compareProperties: MOCK_COMPARE_PROPERTIES,
  budgetInsights: MOCK_BUDGET_INSIGHTS,
};
