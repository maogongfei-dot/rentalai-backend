import "./PropertyIntelligenceCenter.css";

/**
 * Property Intelligence Center — mock preview (frontend only, no API).
 * Phase 9: property investment and rental demand signals.
 */
const mockPropertyIntelligence = {
  property_score: 82,
  investment_rating: "Good",
  rental_demand: "High",
  price_trend: "Stable",
  occupancy_estimate: "92%",
  summary:
    "This property shows good long-term rental potential with stable pricing and strong rental demand.",
};

function getPropertyScoreBadge(score) {
  if (score >= 90) {
    return { label: "Excellent", tone: "excellent" };
  }
  if (score >= 75) {
    return { label: "Good", tone: "good" };
  }
  if (score >= 60) {
    return { label: "Fair", tone: "fair" };
  }
  return { label: "Poor", tone: "poor" };
}

function propertyScoreTone(score) {
  const badge = getPropertyScoreBadge(score);
  return badge.tone;
}

function PropertyIntelligenceOverviewSection({ data }) {
  const scoreBadge = getPropertyScoreBadge(data.property_score);
  const scoreTone = propertyScoreTone(data.property_score);

  return (
    <section
      id="property-intelligence-overview"
      className="property-section"
      aria-labelledby="property-intelligence-heading"
    >
      <header className="property-section__header">
        <h2 id="property-intelligence-heading" className="property-section__title">
          Property Intelligence Overview
        </h2>
        <p className="property-section__subtitle">
          Mock property investment and rental signals for preview — not connected
          to live market data.
        </p>
      </header>

      <div className="card property-panel">
        <div className="property-score-badge-wrap" role="status">
          <p
            className={`property-score-badge property-score-badge--${scoreBadge.tone}`}
          >
            {scoreBadge.label}
          </p>
        </div>

        <div className="property-score-block">
          <div className="property-score-block__main">
            <p className="property-field__label">Property Score</p>
            <p
              className={`property-score-block__value property-score-block__value--${scoreTone}`}
              aria-label={`Property score ${data.property_score} out of 100`}
            >
              <span className="property-score-block__number">
                {data.property_score}
              </span>
              <span className="property-score-block__max">/ 100</span>
            </p>
          </div>
        </div>

        <ul className="property-metrics" aria-label="Property intelligence metrics">
          <li>
            <article className="property-metric">
              <p className="property-field__label">Investment Rating</p>
              <p className="property-field__value property-field__value--metric">
                {data.investment_rating}
              </p>
            </article>
          </li>
          <li>
            <article className="property-metric">
              <p className="property-field__label">Rental Demand</p>
              <p className="property-field__value property-field__value--metric">
                {data.rental_demand}
              </p>
            </article>
          </li>
          <li>
            <article className="property-metric">
              <p className="property-field__label">Price Trend</p>
              <p className="property-field__value property-field__value--metric">
                {data.price_trend}
              </p>
            </article>
          </li>
          <li>
            <article className="property-metric">
              <p className="property-field__label">Occupancy Estimate</p>
              <p className="property-field__value property-field__value--metric">
                {data.occupancy_estimate}
              </p>
            </article>
          </li>
        </ul>

        <div className="property-summary">
          <p className="property-field__label property-field__label--summary">
            Summary
          </p>
          <p className="property-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

export default function PropertyIntelligenceCenter() {
  return (
    <div className="page-shell property-intelligence">
      <header className="property-hero">
        <div className="property-hero__top">
          <p className="property-hero__eyebrow">RentalAI Property Hub</p>
          <span className="property-hero__pill">Preview</span>
        </div>
        <h1 className="property-hero__title">Property Intelligence Center</h1>
        <p className="property-hero__subtitle">
          Review property scores, investment ratings, rental demand, and market
          signals before making a rental or purchase decision.
        </p>
      </header>

      <PropertyIntelligenceOverviewSection data={mockPropertyIntelligence} />
    </div>
  );
}
