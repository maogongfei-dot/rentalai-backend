import { useState } from "react";
import { MOCK_ANALYSIS_HISTORY } from "../data/mockAnalysisHistory.js";
import { MOCK_COMPARE_PROPERTIES } from "../data/mockCompareProperties.js";
import { MOCK_SAVED_PROPERTIES } from "../data/mockSavedProperties.js";
import "./TenantDashboard.css";

const TENANT_MODULES = [
  {
    id: "saved-properties",
    title: "Saved Properties",
    description: "View and manage properties you are interested in.",
  },
  {
    id: "analysis-history",
    title: "Analysis History",
    description:
      "Review your previous RentalAI property and risk analyses.",
  },
  {
    id: "compare-properties",
    title: "Compare Properties",
    description:
      "Compare rent, commute, bills, location, and risk scores.",
  },
  {
    id: "budget-insights",
    title: "Budget Insights",
    description:
      "Understand affordability, rent pressure, and estimated monthly living costs.",
  },
];

function formatRent(amount) {
  return `Â£${amount.toLocaleString("en-GB")} pcm`;
}

function formatBillsIncluded(included) {
  return included ? "Bills included" : "Bills not included";
}

function riskLevelClass(level) {
  const key = level.toLowerCase();
  if (key === "low") return "tenant-saved-risk--low";
  if (key === "high") return "tenant-saved-risk--high";
  return "tenant-saved-risk--medium";
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

const COMPARE_METRICS = [
  { key: "rent", label: "Rent", format: (p) => formatRent(p.rent) },
  { key: "commute_score", label: "Commute score", format: (p) => formatScore(p.commute_score) },
  { key: "bills_score", label: "Bills score", format: (p) => formatScore(p.bills_score) },
  { key: "area_score", label: "Area score", format: (p) => formatScore(p.area_score) },
  { key: "risk_score", label: "Risk score", format: (p) => formatScore(p.risk_score) },
  { key: "final_score", label: "Final score", format: (p) => formatScore(p.final_score), highlight: true },
];

export default function TenantDashboard() {
  const [savedProperties, setSavedProperties] = useState(MOCK_SAVED_PROPERTIES);
  const [detailsHint, setDetailsHint] = useState("");
  const bestCompareOption = getBestCompareOption(MOCK_COMPARE_PROPERTIES);

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
      <header className="page-header">
        <h1 className="page-title">Tenant Center</h1>
        <p className="page-subtitle">
          Manage your saved properties, rental analysis history, comparisons,
          and budget insights.
        </p>
      </header>

      <section
        className="tenant-dashboard-grid"
        aria-label="Tenant center modules"
      >
        {TENANT_MODULES.map((module) => (
          <article
            key={module.id}
            className="card tenant-dashboard-card"
            aria-labelledby={`tenant-module-${module.id}-title`}
          >
            <h2
              id={`tenant-module-${module.id}-title`}
              className="tenant-dashboard-card-title"
            >
              {module.title}
            </h2>
            <p className="tenant-dashboard-card-text">{module.description}</p>
            <span className="tenant-dashboard-card-badge">Coming soon</span>
          </article>
        ))}
      </section>

      <section
        id="saved-properties"
        className="tenant-saved-section"
        aria-labelledby="tenant-saved-heading"
      >
        <header className="tenant-saved-header">
          <h2 id="tenant-saved-heading" className="section-title">
            Saved Properties
          </h2>
          <p className="tenant-saved-intro">
            Properties you have saved for later review. Data shown here is mock
            only and is not stored on the server.
          </p>
        </header>

        {detailsHint ? (
          <p className="tenant-saved-hint" role="status">
            {detailsHint}
          </p>
        ) : null}

        {savedProperties.length === 0 ? (
          <p className="tenant-saved-empty text-muted">
            No saved properties yet. Save a listing from search or analysis to
            see it here.
          </p>
        ) : (
          <ul className="tenant-saved-list">
            {savedProperties.map((property) => (
              <li key={property.id}>
                <article
                  className="card tenant-saved-card"
                  aria-label={property.title}
                >
                  <div className="tenant-saved-card-top">
                    <h3 className="tenant-saved-card-title">{property.title}</h3>
                    <p className="tenant-saved-location">{property.location}</p>
                  </div>

                  <dl className="tenant-saved-meta">
                    <div className="tenant-saved-meta-row">
                      <dt>Rent</dt>
                      <dd>{formatRent(property.rent)}</dd>
                    </div>
                    <div className="tenant-saved-meta-row">
                      <dt>Bedrooms</dt>
                      <dd>
                        {property.bedrooms}{" "}
                        {property.bedrooms === 1 ? "bedroom" : "bedrooms"}
                      </dd>
                    </div>
                    <div className="tenant-saved-meta-row">
                      <dt>Bills</dt>
                      <dd>{formatBillsIncluded(property.bills_included)}</dd>
                    </div>
                    <div className="tenant-saved-meta-row">
                      <dt>Risk level</dt>
                      <dd>
                        <span
                          className={`tenant-saved-risk ${riskLevelClass(property.risk_level)}`}
                        >
                          {property.risk_level}
                        </span>
                      </dd>
                    </div>
                    <div className="tenant-saved-meta-row">
                      <dt>Score</dt>
                      <dd className="tenant-saved-score">{property.score}/100</dd>
                    </div>
                  </dl>

                  <div className="tenant-saved-actions">
                    <button
                      type="button"
                      className="btn tenant-saved-btn"
                      onClick={() => handleViewDetails(property)}
                    >
                      View details
                    </button>
                    <button
                      type="button"
                      className="btn tenant-saved-btn tenant-saved-btn--remove"
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
        className="tenant-history-section"
        aria-labelledby="tenant-history-heading"
      >
        <header className="tenant-history-header">
          <h2 id="tenant-history-heading" className="section-title">
            Analysis History
          </h2>
          <p className="tenant-history-intro">
            Your previous RentalAI property and risk analyses. Data shown here is
            mock only and is not stored on the server.
          </p>
        </header>

        <ul className="tenant-history-list">
          {MOCK_ANALYSIS_HISTORY.map((record) => (
            <li key={record.id}>
              <article
                className="card tenant-history-card"
                aria-label={record.property_title}
              >
                <div className="tenant-history-card-top">
                  <h3 className="tenant-history-card-title">
                    {record.property_title}
                  </h3>
                  <p className="tenant-history-location">{record.location}</p>
                </div>

                <dl className="tenant-history-meta">
                  <div className="tenant-history-meta-row">
                    <dt>Analysis type</dt>
                    <dd>{record.analysis_type}</dd>
                  </div>
                  <div className="tenant-history-meta-row">
                    <dt>Final score</dt>
                    <dd className="tenant-history-score">
                      {record.final_score}/100
                    </dd>
                  </div>
                  <div className="tenant-history-meta-row">
                    <dt>Risk level</dt>
                    <dd>
                      <span
                        className={`tenant-saved-risk ${riskLevelClass(record.risk_level)}`}
                      >
                        {record.risk_level}
                      </span>
                    </dd>
                  </div>
                  <div className="tenant-history-meta-row">
                    <dt>Date</dt>
                    <dd>{formatAnalysisDate(record.created_at)}</dd>
                  </div>
                </dl>

                <p className="tenant-history-summary">{record.summary}</p>

                <div className="tenant-history-actions">
                  <button
                    type="button"
                    className="btn tenant-history-btn"
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
        className="tenant-compare-section"
        aria-labelledby="tenant-compare-heading"
      >
        <header className="tenant-compare-header">
          <h2 id="tenant-compare-heading" className="section-title">
            Compare Properties
          </h2>
          <p className="tenant-compare-intro">
            Side-by-side comparison of rent, commute, bills, area, and risk
            scores. Mock data only â€?not stored on the server.
          </p>
        </header>

        {bestCompareOption ? (
          <p className="tenant-compare-verdict" role="status">
            Best option based on current mock scores:{" "}
            <strong>{bestCompareOption.title}</strong>
          </p>
        ) : null}

        <div className="card tenant-compare-table-wrap">
          <div className="tenant-compare-scroll">
            <table className="tenant-compare-table">
              <caption className="tenant-compare-caption">
                Property comparison table
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="tenant-compare-metric-col">
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
                      metric.highlight ? "tenant-compare-row--highlight" : undefined
                    }
                  >
                    <th scope="row" className="tenant-compare-metric-col">
                      {metric.label}
                    </th>
                    {MOCK_COMPARE_PROPERTIES.map((property) => {
                      const isBest =
                        bestCompareOption?.id === property.id &&
                        metric.key === "final_score";
                      return (
                        <td
                          key={`${property.id}-${metric.key}`}
                          className={isBest ? "tenant-compare-cell--best" : undefined}
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
    </div>
  );
}
