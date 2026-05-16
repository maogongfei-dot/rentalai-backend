import { aiGuides } from "../data/aiGuides.js";

const INTENT_TO_CATEGORY = {
  property_search: "property",
  contract_help: "contract",
  landlord_help: "landlord",
  area_info: "property",
  dispute_help: "contract",
};

export function getAllGuides() {
  return aiGuides.slice();
}

export function getGuidesByCategory(category) {
  return aiGuides.filter((g) => g.category === category);
}

export function getGuideById(id) {
  return aiGuides.find((g) => g.id === id);
}

export function getRecommendedGuidesByIntent(intent) {
  const key = (intent ?? "").trim();
  if (!key || key === "general") {
    return aiGuides.slice(0, 3);
  }
  const category = INTENT_TO_CATEGORY[key];
  if (!category) {
    return aiGuides.slice(0, 3);
  }
  return getGuidesByCategory(category);
}
