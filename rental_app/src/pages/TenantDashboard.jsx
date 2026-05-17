import { useMemo, useState } from "react";
import { MOCK_ANALYSIS_HISTORY } from "../data/mockAnalysisHistory.js";
import { MOCK_BUDGET_INSIGHTS } from "../data/mockBudgetInsights.js";
import { MOCK_COMPARE_PROPERTIES } from "../data/mockCompareProperties.js";
import { MOCK_SAVED_PROPERTIES } from "../data/mockSavedProperties.js";
import "./TenantDashboard.css";

const QUICK_NAV = [
  { id: "saved-properties", label: "Saved" },
  { id: "analysis-history", label: "History" },
  { id: "compare-properties", label: "Compare" },
  { id: "budget-insights", label: "Budget" },
];

function formatRent(amount) {
  return `\u00A3${amount.toLocaleString("en-GB")} pcm`;
}

function formatMoney(amount) {
  return `\u00A3${amount.toLocaleString("en-GB")}`;
}

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

function riskBadgeClass(level) {
  const key = level.toLowerCase();
  if (key === "low") return "tenant-badge--low";
  if (key === "high") return "tenant-badge--high";
  return "tenant-badge--medium";
}

function formatBillsIncluded(included) {
  return included ? "Bills included" : "Bills not included";
}

function getBestCompareOption(properties) {
  if (properties.length === 0) return null;
  return properties.reduce((best, current) =>
    current.final_score > best.final_score ? current : best,
  );
}

function formatScore(value) {
  return `${value}/100`;
}

function formatAnalysisDate(isoDate) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function ScoreBadge({ value }) {
  return (
    <span className="tenant-score-badge" aria-label={`Score ${value} out of 100`}>
      <span className="tenant-score-badge__value">{value}</span>
      <span className="tenant-score-badge__max">/100</span>
    </span>
  );
}

function RiskBadge({ level }) {
  return (
    <span className={`tenant-badge ${riskBadgeClass(level)}`}>{level}</span>
  );
}

function PanelHeader({ id, title, description }) {
  return (
    <header className="tenant-panel__header">
      <h2 id={`${id}-heading`} className="tenant-panel__title">
        {title}
      </h2>
      <p className="tenant-panel__desc">{description}</p>
    </header>
  );
}

const COMPARE_METRICS = [
  { key: "rent", label: "Rent", format: (p) => formatRent(p.rent) },
  {
    key: "commute_score",
    label: "Commute score",
    format: (p) => formatScore(p.commute_score),
  },
  {
    key: "bills_score",
    label: "Bills score",
    format: (p) => formatScore(p.bills_score),
  },
  {
    key: "area_score",
    label: "Area score",
    format: (p) => formatScore(p.area_score),
  },
  {
    key: "risk_score",
    label: "Risk score",
    format: (p) => formatScore(p.risk_score),
  },
  {
    key: "final_score",
    label: "Final score",
    format: (p) => formatScore(p.final_score),
    highlight: true,
  },
];

export default function TenantDashboard() {
  const [savedProperties, setSavedProperties] = useState(MOCK_SAVED_PROPERTIES);
  const [detailsHint, setDetailsHint] = useState("");

  const budget = MOCK_BUDGET_INSIGHTS;
  const affordabilityHint = getAffordabilityHint(budget.affordability_score);
  const bestCompareOption = getBestCompareOption(MOCK_COMPARE_PROPERTIES);

  const bestPropertyScore = useMemo(() => {
    const scores = [
      ...MOCK_COMPARE_PROPERTIES.map((p) => p.final_score),
      ...savedProperties.map((p) => p.score),
    ];
    return scores.length ? Math.max(...scores) : 0;
  }, [savedProperties]);

  const summaryCards = useMemo(
    () => [
      {
        id: "summary-saved",
        label: "Saved Properties",
        value: String(savedProperties.length),
        detail: "properties in your list",
        href: "#saved-properties",
      },
      {
        id: "summary-analysis",
        label: "Analysis Records",
        value: String(MOCK_ANALYSIS_HISTORY.length),
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
        detail: `${budget.affordability_score}/100 affordability`,
        href: "#budget-insights",
        valueClass: affordabilityHint.className,
      },
    ],
    [savedProperties.length, bestPropertyScore, bestCompareOption, affordabilityHint, budget.affordability_score],
  );

  function handleViewDetails(property) {
    console.log("View saved property details:", property);
    setDetailsHint(`Details preview: ${property.title} (${property.location})`);
  }

  function handleRemove(propertyId) {
    setSavedProperties((prev) => prev.filter((p) => p.id !== propertyId));
    setDetailsHint("");
  }

  function handleViewReport(record) {
    console.log("View analysis report:", record);
    window.alert(
      `Report: ${record.property_title}\nType: ${record.analysis_type}\nScore: ${record.final_score}/100`,
    );
  }

  return (
    <div className="page-shell tenant-dashboard">
      <header className="tenant-hero">
        <p className="tenant-hero__eyebrow">RentalAI Tenant Hub</p>
        <h1 className="tenant-hero__title">Tenant Center</h1>
        <p className="tenant-hero__subtitle">
          Manage your saved properties, rental analysis history, comparisons, and
          budget insights in one place.
        </p>
      </header>

      <section className="tenant-summary" aria-label="Dashboard summary">
        <ul className="tenant-summary__grid">
          {summaryCards.map((card) => (
            <li key={card.id}>
              <a href={card.href} className="card tenant-summary__card">
                <span className="tenant-summary__label">{card.label}</span>
                <span
                  className={`tenant-summary__value ${card.valueClass ?? ""}`.trim()}
                >
                  {card.value}
                </span>
                <span className="tenant-summary__detail">{card.detail}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <nav className="tenant-quick-nav" aria-label="Jump to section">
        {QUICK_NAV.map((item) => (
          <a key={item.id} href={`#${item.id}`} className="tenant-quick-nav__link">
            {item.label}
          </a>
        ))}
      </nav>

      <div className="tenant-panels">
        <section
          id="saved-properties"
          className="tenant-panel"
          aria-labelledby="saved-properties-heading"
        >
          <PanelHeader
            id="saved-properties"
            title="Saved Properties"
            description="Properties you have saved for later review. Mock data only."
          />

          {detailsHint ? (
            <p className="tenant-callout tenant-callout--info" role="status">
              {detailsHint}
            </p>
          ) : null}

          {savedProperties.length === 0 ? (
            <p className="tenant-empty text-muted">
              No saved properties yet. Save a listing from search or analysis to
              see it here.
            </p>
          ) : (
            <ul className="tenant-item-list">
              {savedProperties.map((property) => (
                <li key={property.id}>
                  <article className="card tenant-item-card">
                    <div className="tenant-item-card__head">
                      <h3 className="tenant-item-card__title">{property.title}</h3>
                      <p className="tenant-item-card__meta">{property.location}</p>
                    </div>
                    <dl className="tenant-meta-grid">
                      <div className="tenant-meta-grid__row">
                        <dt>Rent</dt>
                        <dd>{formatRent(property.rent)}</dd>
                      </div>
                      <div className="tenant-meta-grid__row">
                        <dt>Bedrooms</dt>
                        <dd>
                          {property.bedrooms}{" "}
                          {property.bedrooms === 1 ? "bedroom" : "bedrooms"}
                        </dd>
                      </div>
                      <div className="tenant-meta-grid__row">
                        <dt>Bills</dt>
                        <dd>{formatBillsIncluded(property.bills_included)}</dd>
                      </div>
                      <div className="tenant-meta-grid__row">
                        <dt>Risk level</dt>
                        <dd>
                          <RiskBadge level={property.risk_level} />
                        </dd>
                      </div>
                      <div className="tenant-meta-grid__row">
                        <dt>Score</dt>
                        <dd>
                          <ScoreBadge value={property.score} />
                        </dd>
                      </div>
                    </dl>
                    <div className="tenant-actions">
                      <button
                        type="button"
                        className="btn tenant-btn"
                        onClick={() => handleViewDetails(property)}
                      >
                        View details
                      </button>
                      <button
                        type="button"
                        className="btn tenant-btn tenant-btn--ghost"
                        onClick={() => handleRemove(property.id)}
                      >
                        Remove
                      </button>
                    </div>
                  </article>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section
          id="analysis-history"
          className="tenant-panel"
          aria-labelledby="analysis-history-heading"
        >
          <PanelHeader
            id="analysis-history"
            title="Analysis History"
            description="Your previous RentalAI property and risk analyses. Mock data only."
          />

          <ul className="tenant-item-list">
            {MOCK_ANALYSIS_HISTORY.map((record) => (
              <li key={record.id}>
                <article className="card tenant-item-card">
                  <div className="tenant-item-card__head">
                    <h3 className="tenant-item-card__title">
                      {record.property_title}
                    </h3>
                    <p className="tenant-item-card__meta">{record.location}</p>
                  </div>
                  <dl className="tenant-meta-grid">
                    <div className="tenant-meta-grid__row">
                      <dt>Analysis type</dt>
                      <dd>{record.analysis_type}</dd>
                    </div>
                    <div className="tenant-meta-grid__row">
                      <dt>Final score</dt>
                      <dd>
                        <ScoreBadge value={record.final_score} />
                      </dd>
                    </div>
                    <div className="tenant-meta-grid__row">
                      <dt>Risk level</dt>
                      <dd>
                        <RiskBadge level={record.risk_level} />
                      </dd>
                    </div>
                    <div className="tenant-meta-grid__row">
                      <dt>Date</dt>
                      <dd>{formatAnalysisDate(record.created_at)}</dd>
                    </div>
                  </dl>
                  <p className="tenant-item-card__summary">{record.summary}</p>
                  <div className="tenant-actions">
                    <button
                      type="button"
                      className="btn tenant-btn"
                      onClick={() => handleViewReport(record)}
                    >
                      View report
                    </button>
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </section>

        <section
          id="compare-properties"
          className="tenant-panel"
          aria-labelledby="compare-properties-heading"
        >
          <PanelHeader
            id="compare-properties"
            title="Compare Properties"
            description="Side-by-side comparison of rent, commute, bills, area, and risk scores."
          />

          {bestCompareOption ? (
            <p className="tenant-callout tenant-callout--info" role="status">
              Best option based on current mock scores:{" "}
              <strong>{bestCompareOption.title}</strong>
            </p>
          ) : null}

          <div className="card tenant-compare-wrap">
            <div className="tenant-compare-scroll">
              <table className="tenant-compare-table">
                <caption className="tenant-sr-only">
                  Property comparison table
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="tenant-compare-table__metric">
                      Metric
                    </th>
                    {MOCK_COMPARE_PROPERTIES.map((property) => (
                      <th key={property.id} scope="col">
                        {property.title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARE_METRICS.map((metric) => (
                    <tr
                      key={metric.key}
                      className={
                        metric.highlight
                          ? "tenant-compare-table__row--highlight"
                          : undefined
                      }
                    >
                      <th scope="row" className="tenant-compare-table__metric">
                        {metric.label}
                      </th>
                      {MOCK_COMPARE_PROPERTIES.map((property) => {
                        const isBest =
                          bestCompareOption?.id === property.id &&
                          metric.key === "final_score";
                        return (
                          <td
                            key={`${property.id}-${metric.key}`}
                            className={
                              isBest ? "tenant-compare-table__cell--best" : undefined
                            }
                          >
                            {metric.format(property)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section
          id="budget-insights"
          className="tenant-panel"
          aria-labelledby="budget-insights-heading"
        >
          <PanelHeader
            id="budget-insights"
            title="Budget Insights"
            description="Estimated monthly affordability from your target rent and living costs."
          />

          <p
            className={`tenant-callout ${affordabilityHint.className}`}
            role="status"
          >
            {affordabilityHint.text}
          </p>

          <article className="card tenant-item-card" aria-label="Budget breakdown">
            <dl className="tenant-meta-grid tenant-meta-grid--budget">
              <div className="tenant-meta-grid__row">
                <dt>Monthly Income</dt>
                <dd>{formatMoney(budget.monthly_income)}</dd>
              </div>
              <div className="tenant-meta-grid__row">
                <dt>Target Rent</dt>
                <dd>{formatRent(budget.target_rent)}</dd>
              </div>
              <div className="tenant-meta-grid__row">
                <dt>Estimated Bills</dt>
                <dd>{formatMoney(budget.estimated_bills)}</dd>
              </div>
              <div className="tenant-meta-grid__row">
                <dt>Transport Cost</dt>
                <dd>{formatMoney(budget.estimated_transport)}</dd>
              </div>
              <div className="tenant-meta-grid__row">
                <dt>Food Cost</dt>
                <dd>{formatMoney(budget.estimated_food_cost)}</dd>
              </div>
              <div className="tenant-meta-grid__row tenant-meta-grid__row--emphasis">
                <dt>Remaining Balance</dt>
                <dd className="tenant-meta-grid__value--primary">
                  {formatMoney(budget.estimated_remaining_balance)}
                </dd>
              </div>
              <div className="tenant-meta-grid__row tenant-meta-grid__row--emphasis">
                <dt>Affordability Score</dt>
                <dd>
                  <ScoreBadge value={budget.affordability_score} />
                </dd>
              </div>
              <div className="tenant-meta-grid__row">
                <dt>Rent Pressure Level</dt>
                <dd>
                  <RiskBadge level={budget.rent_pressure_level} />
                </dd>
              </div>
            </dl>
          </article>
        </section>
      </div>
    </div>
  );
}
