import "./LandlordCenter.css";

/**
 * Landlord Center — mock reputation preview (frontend only, no API).
 * Phase 8: landlord trust, complaints, and rental history signals.
 */
const mockLandlordOverview = {
  landlord_name: "Sample Landlord",
  trust_score: 76,
  total_properties: 3,
  complaint_count: 1,
  response_speed: "Usually responds within 24 hours",
  verification_status: "Partially verified",
  summary:
    "This landlord shows a generally acceptable profile, but renters should review complaint history and contract terms carefully.",
};

const mockComplaintSignals = {
  complaint_count: 1,
  complaint_types: ["Delayed repairs", "Deposit dispute"],
  complaint_severity: "Medium",
  unresolved_complaints: 1,
  recent_complaint:
    "Tenant reported delayed repair response within the last 6 months.",
  summary:
    "There are some complaint signals, mainly around repair response and deposit handling. Renters should review contract terms and communication records carefully.",
};

function trustScoreTone(score) {
  if (score >= 80) return "high";
  if (score >= 60) return "mid";
  return "low";
}

function getTrustScoreHint(score) {
  if (score >= 80) {
    return { label: "High trust landlord", tone: "high" };
  }
  if (score >= 60) {
    return { label: "Moderate trust landlord", tone: "mid" };
  }
  return { label: "Caution recommended", tone: "low" };
}

function getComplaintRiskHint(unresolvedComplaints) {
  if (unresolvedComplaints >= 2) {
    return { label: "High complaint risk", tone: "low" };
  }
  if (unresolvedComplaints === 1) {
    return { label: "Some complaint risk", tone: "mid" };
  }
  return { label: "No major complaint signal", tone: "high" };
}

function ComplaintTypeList({ items }) {
  if (!items?.length) {
    return <p className="landlord-complaint-empty">None listed</p>;
  }

  return (
    <ul className="landlord-complaint-types">
      {items.map((item) => (
        <li key={item}>
          <span className="landlord-complaint-types__item">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function LandlordReputationOverviewSection({ data }) {
  const hint = getTrustScoreHint(data.trust_score);
  const scoreTone = trustScoreTone(data.trust_score);

  return (
    <section
      id="landlord-reputation-overview"
      className="landlord-overview"
      aria-labelledby="landlord-overview-heading"
    >
      <header className="landlord-overview__header">
        <h2 id="landlord-overview-heading" className="landlord-overview__title">
          Landlord Reputation Overview
        </h2>
        <p className="landlord-overview__subtitle">
          Mock landlord trust signals for preview — not connected to live
          reputation or complaint data.
        </p>
      </header>

      <div className="card landlord-overview-panel">
        <div className="landlord-overview-identity">
          <p className="landlord-overview-identity__label">Landlord Name</p>
          <p className="landlord-overview-identity__value">{data.landlord_name}</p>
        </div>

        <div className="landlord-overview-trust">
          <div className="landlord-overview-trust__main">
            <p className="landlord-overview-trust__label">Trust Score</p>
            <p
              className={`landlord-overview-trust__value landlord-overview-trust__value--${scoreTone}`}
              aria-label={`Trust score ${data.trust_score} out of 100`}
            >
              <span className="landlord-overview-trust__number">
                {data.trust_score}
              </span>
              <span className="landlord-overview-trust__max">/ 100</span>
            </p>
          </div>
          <p
            className={`landlord-overview-hint landlord-overview-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <ul className="landlord-overview-metrics" aria-label="Landlord metrics">
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Total Properties</p>
              <p className="landlord-overview-metric__value">
                {data.total_properties}
              </p>
            </article>
          </li>
          <li>
            <article
              className={`landlord-overview-metric landlord-overview-metric--${data.complaint_count > 0 ? "caution" : "neutral"}`}
            >
              <p className="landlord-overview-metric__label">Complaint Count</p>
              <p className="landlord-overview-metric__value">
                {data.complaint_count}
              </p>
            </article>
          </li>
        </ul>

        <div className="landlord-overview-details">
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">Response Speed</p>
            <p className="landlord-overview-detail__value">{data.response_speed}</p>
          </div>
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">Verification Status</p>
            <p className="landlord-overview-detail__badge">
              {data.verification_status}
            </p>
          </div>
        </div>

        <div className="landlord-overview-summary">
          <p className="landlord-overview-summary__label">Summary</p>
          <p className="landlord-overview-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

function ComplaintSignalsSection({ data }) {
  const hint = getComplaintRiskHint(data.unresolved_complaints);

  return (
    <section
      id="complaint-signals"
      className="landlord-complaints"
      aria-labelledby="complaint-signals-heading"
    >
      <header className="landlord-complaints__header">
        <h2 id="complaint-signals-heading" className="landlord-complaints__title">
          Complaint Signals
        </h2>
        <p className="landlord-complaints__subtitle">
          Mock complaint and dispute signals for preview — not connected to live
          complaint records.
        </p>
      </header>

      <div className="card landlord-complaints-panel">
        <div className="landlord-complaints-risk">
          <p
            className={`landlord-overview-hint landlord-overview-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <ul className="landlord-overview-metrics" aria-label="Complaint metrics">
          <li>
            <article
              className={`landlord-overview-metric landlord-overview-metric--${data.complaint_count > 0 ? "caution" : "neutral"}`}
            >
              <p className="landlord-overview-metric__label">Complaint Count</p>
              <p className="landlord-overview-metric__value">
                {data.complaint_count}
              </p>
            </article>
          </li>
          <li>
            <article
              className={`landlord-overview-metric landlord-overview-metric--${data.unresolved_complaints > 0 ? "caution" : "neutral"}`}
            >
              <p className="landlord-overview-metric__label">
                Unresolved Complaints
              </p>
              <p className="landlord-overview-metric__value">
                {data.unresolved_complaints}
              </p>
            </article>
          </li>
        </ul>

        <div className="landlord-complaints-block">
          <p className="landlord-overview-detail__label">Complaint Types</p>
          <ComplaintTypeList items={data.complaint_types} />
        </div>

        <div className="landlord-overview-detail landlord-complaints-severity">
          <p className="landlord-overview-detail__label">Complaint Severity</p>
          <p className="landlord-complaints-severity__badge">
            {data.complaint_severity}
          </p>
        </div>

        <div className="landlord-overview-detail">
          <p className="landlord-overview-detail__label">Recent Complaint</p>
          <p className="landlord-overview-detail__value">{data.recent_complaint}</p>
        </div>

        <div className="landlord-overview-summary">
          <p className="landlord-overview-summary__label">Summary</p>
          <p className="landlord-overview-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

export default function LandlordCenter() {
  return (
    <div className="page-shell landlord-center">
      <header className="landlord-center-hero">
        <div className="landlord-center-hero__top">
          <p className="landlord-center-hero__eyebrow">RentalAI Trust Hub</p>
          <span className="landlord-center-hero__pill">Preview</span>
        </div>
        <h1 className="landlord-center-hero__title">Landlord Center</h1>
        <p className="landlord-center-hero__subtitle">
          Review landlord reputation, rental history, complaint signals, and trust
          indicators.
        </p>
      </header>

      <LandlordReputationOverviewSection data={mockLandlordOverview} />
      <ComplaintSignalsSection data={mockComplaintSignals} />
    </div>
  );
}
