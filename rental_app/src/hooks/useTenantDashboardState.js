import { useCallback, useMemo, useState } from "react";
import {
  MOCK_ANALYSIS_HISTORY,
  MOCK_BUDGET_INSIGHTS,
  MOCK_COMPARE_PROPERTIES,
  MOCK_SAVED_PROPERTIES,
} from "../data/tenantMockData.js";

function getAffordabilityHint(score) {
  if (score >= 75) {
    return {
      text: "Affordable",
      className: "tenant-callout--success",
    };
  }
  if (score >= 50) {
    return {
      text: "Moderate pressure",
      className: "tenant-callout--warning",
    };
  }
  return {
    text: "High rent pressure",
    className: "tenant-callout--danger",
  };
}

function getBestCompareOption(properties) {
  if (properties.length === 0) return null;
  return properties.reduce((best, current) =>
    current.final_score > best.final_score ? current : best,
  );
}

function computeBestPropertyScore(savedProperties, compareProperties) {
  const scores = [
    ...compareProperties.map((p) => p.final_score),
    ...savedProperties.map((p) => p.score),
  ];
  return scores.length ? Math.max(...scores) : 0;
}

function buildSummaryCards({
  savedCount,
  analysisCount,
  bestPropertyScore,
  bestCompareOption,
  affordabilityHint,
  budgetInsights,
}) {
  return [
    {
      id: "summary-saved",
      label: "Saved Properties",
      value: String(savedCount),
      detail: "properties in your list",
      href: "#saved-properties",
    },
    {
      id: "summary-analysis",
      label: "Analysis Records",
      value: String(analysisCount),
      detail: "completed analyses",
      href: "#analysis-history",
    },
    {
      id: "summary-best",
      label: "Best Property Score",
      value: String(bestPropertyScore),
      detail: bestCompareOption?.title ?? "No comparison data",
      href: "#compare-properties",
    },
    {
      id: "summary-budget",
      label: "Budget Status",
      value: affordabilityHint.text,
      detail: `${budgetInsights.affordability_score}/100 affordability`,
      href: "#budget-insights",
      valueClass: affordabilityHint.className,
    },
  ];
}

/**
 * Tenant Center state — mock/static data today; swap loaders for API later.
 */
export function useTenantDashboardState() {
  const [savedProperties, setSavedProperties] = useState(MOCK_SAVED_PROPERTIES);
  const [savedPropertyPreview, setSavedPropertyPreview] = useState("");

  const analysisHistory = MOCK_ANALYSIS_HISTORY;
  const compareProperties = MOCK_COMPARE_PROPERTIES;
  const budgetInsights = MOCK_BUDGET_INSIGHTS;

  const affordabilityHint = useMemo(
    () => getAffordabilityHint(budgetInsights.affordability_score),
    [budgetInsights.affordability_score],
  );

  const bestCompareOption = useMemo(
    () => getBestCompareOption(compareProperties),
    [compareProperties],
  );

  const bestPropertyScore = useMemo(
    () => computeBestPropertyScore(savedProperties, compareProperties),
    [savedProperties, compareProperties],
  );

  const summaryCards = useMemo(
    () =>
      buildSummaryCards({
        savedCount: savedProperties.length,
        analysisCount: analysisHistory.length,
        bestPropertyScore,
        bestCompareOption,
        affordabilityHint,
        budgetInsights,
      }),
    [
      savedProperties.length,
      analysisHistory.length,
      bestPropertyScore,
      bestCompareOption,
      affordabilityHint,
      budgetInsights,
    ],
  );

  const handleViewSavedProperty = useCallback((property) => {
    console.log("View saved property details:", property);
    setSavedPropertyPreview(
      `Details preview: ${property.title} (${property.location})`,
    );
  }, []);

  const handleRemoveSavedProperty = useCallback((id) => {
    setSavedProperties((prev) => prev.filter((p) => p.id !== id));
    setSavedPropertyPreview("");
  }, []);

  const handleViewAnalysisReport = useCallback((record) => {
    console.log("View analysis report:", record);
    window.alert(
      `Report: ${record.property_title}\nType: ${record.analysis_type}\nScore: ${record.final_score}/100`,
    );
  }, []);

  return {
    savedProperties,
    analysisHistory,
    compareProperties,
    budgetInsights,
    savedPropertyPreview,
    summaryCards,
    bestCompareOption,
    affordabilityHint,
    handleViewSavedProperty,
    handleRemoveSavedProperty,
    handleViewAnalysisReport,
  };
}
