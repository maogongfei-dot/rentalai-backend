import { useState } from "react";
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
  return `£${amount.toLocaleString("en-GB")} pcm`;
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

export default function TenantDashboard() {
  const [savedProperties, setSavedProperties] = useState(MOCK_SAVED_PROPERTIES);
  const [detailsHint, setDetailsHint] = useState("");

  function handleViewDetails(property) {
    console.log("View saved property details:", property);
    setDetailsHint(`Details preview: ${property.title} (${property.location})`);
  }

  function handleRemove(propertyId) {
    setSavedProperties((prev) => prev.filter((p) => p.id !== propertyId));
    setDetailsHint("");
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
    </div>
  );
}
