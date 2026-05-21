/** Area Analysis Center — mock area score (frontend only, no API) */

export const mockAreaScore = {
  postcode: "M1 4BT",
  area_name: "Northern Quarter, Manchester",
  overall_score: 82,
  transport_score: 88,
  safety_score: 74,
  facilities_score: 85,
  school_score: 79,
  rent_value_score: 81,
  summary:
    "A well-connected central neighbourhood with strong daily amenities and good rental demand. Safety scores are moderate — visit at different times and check recent local reports before committing.",
};

export function getOverallScoreHint(overallScore) {
  if (overallScore >= 80) {
    return {
      label: "Strong rental area",
      tone: "strong",
    };
  }
  if (overallScore >= 60) {
    return {
      label: "Balanced area",
      tone: "balanced",
    };
  }
  return {
    label: "Needs careful review",
    tone: "caution",
  };
}
