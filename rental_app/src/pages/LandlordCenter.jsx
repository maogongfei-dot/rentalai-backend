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

const mockRentalHistory = {
  years_active: 4,
  estimated_tenancies: 12,
  repeat_tenant_signal:
    "Some tenants appear to have stayed for more than 12 months",
  average_tenancy_length: "10 months",
  rent_increase_signal: "No strong rent increase pattern detected",
  property_maintenance_signal: "Mixed maintenance feedback",
  summary:
    "This landlord has some rental history signals, with moderate experience and mixed maintenance feedback.",
};

const mockVerificationSignals = {
  identity_verified: true,
  email_verified: true,
  phone_verified: true,
  ownership_verification: "Not verified",
  response_rate: "82%",
  average_response_time: "6 hours",
  summary:
    "This landlord has basic identity and contact verification, but property ownership has not yet been verified.",
};

const mockRiskSummary = {
  overall_risk: "Medium Risk",
  trust_score: 78,
  complaint_level: "Low",
  rental_history_level: "Moderate",
  verification_level: "Basic",
  recommendation:
    "Proceed with normal due diligence before signing a tenancy agreement.",
  summary:
    "Overall landlord risk appears moderate based on available reputation, complaint, rental history and verification signals.",
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

function getRentalHistoryHint(yearsActive) {
  if (yearsActive >= 5) {
    return { label: "Experienced landlord", tone: "high" };
  }
  if (yearsActive >= 2) {
    return { label: "Some rental history", tone: "mid" };
  }
  return { label: "Limited rental history", tone: "low" };
}

function getVerificationHints(data) {
  const hints = [];

  if (data.identity_verified && data.email_verified && data.phone_verified) {
    hints.push({
      label: "Basic landlord verification complete",
      tone: "high",
    });
  }

  if (data.ownership_verification === "Verified") {
    hints.push({ label: "Property ownership verified", tone: "high" });
  } else {
    hints.push({ label: "Property ownership not verified", tone: "mid" });
  }

  return hints;
}

function getRiskLevelHint(trustScore) {
  if (trustScore >= 85) {
    return { label: "Low Risk", tone: "high" };
  }
  if (trustScore >= 60) {
    return { label: "Medium Risk", tone: "mid" };
  }
  return { label: "High Risk", tone: "low" };
}

function VerificationStatusField({ label, verified }) {
  return (
    <div className="landlord-overview-detail">
      <p className="landlord-overview-detail__label">{label}</p>
      <p
        className={`landlord-verification-status landlord-verification-status--${verified ? "yes" : "no"}`}
      >
        {verified ? "Verified" : "Not verified"}
      </p>
    </div>
  );
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

function RentalHistorySignalsSection({ data }) {
  const hint = getRentalHistoryHint(data.years_active);

  return (
    <section
      id="rental-history-signals"
      className="landlord-history"
      aria-labelledby="rental-history-heading"
    >
      <header className="landlord-history__header">
        <h2 id="rental-history-heading" className="landlord-history__title">
          Rental History Signals
        </h2>
        <p className="landlord-history__subtitle">
          Mock rental history and tenancy patterns for preview — not connected
          to live tenancy records.
        </p>
      </header>

      <div className="card landlord-history-panel">
        <div className="landlord-history-hint-wrap">
          <p
            className={`landlord-overview-hint landlord-overview-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <ul className="landlord-overview-metrics" aria-label="Rental history metrics">
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Years Active</p>
              <p className="landlord-overview-metric__value">{data.years_active}</p>
            </article>
          </li>
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Estimated Tenancies</p>
              <p className="landlord-overview-metric__value">
                {data.estimated_tenancies}
              </p>
            </article>
          </li>
        </ul>

        <div className="landlord-overview-details">
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">Repeat Tenant Signal</p>
            <p className="landlord-overview-detail__value">
              {data.repeat_tenant_signal}
            </p>
          </div>
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">Average Tenancy Length</p>
            <p className="landlord-overview-detail__value">
              {data.average_tenancy_length}
            </p>
          </div>
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">Rent Increase Signal</p>
            <p className="landlord-overview-detail__value">
              {data.rent_increase_signal}
            </p>
          </div>
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">
              Property Maintenance Signal
            </p>
            <p className="landlord-overview-detail__value">
              {data.property_maintenance_signal}
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

function LandlordVerificationSignalsSection({ data }) {
  const hints = getVerificationHints(data);

  return (
    <section
      id="landlord-verification-signals"
      className="landlord-verification"
      aria-labelledby="landlord-verification-heading"
    >
      <header className="landlord-verification__header">
        <h2
          id="landlord-verification-heading"
          className="landlord-verification__title"
        >
          Landlord Verification Signals
        </h2>
        <p className="landlord-verification__subtitle">
          Mock identity and contact verification signals for preview — not
          connected to live verification services.
        </p>
      </header>

      <div className="card landlord-verification-panel">
        <div className="landlord-verification-hints" role="status">
          {hints.map((hint) => (
            <p
              key={hint.label}
              className={`landlord-overview-hint landlord-overview-hint--${hint.tone}`}
            >
              {hint.label}
            </p>
          ))}
        </div>

        <div className="landlord-overview-details">
          <VerificationStatusField
            label="Identity Verified"
            verified={data.identity_verified}
          />
          <VerificationStatusField
            label="Email Verified"
            verified={data.email_verified}
          />
          <VerificationStatusField
            label="Phone Verified"
            verified={data.phone_verified}
          />
          <div className="landlord-overview-detail">
            <p className="landlord-overview-detail__label">
              Ownership Verification
            </p>
            <p
              className={`landlord-verification-status landlord-verification-status--${data.ownership_verification === "Verified" ? "yes" : "no"}`}
            >
              {data.ownership_verification}
            </p>
          </div>
        </div>

        <ul
          className="landlord-overview-metrics"
          aria-label="Verification response metrics"
        >
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Response Rate</p>
              <p className="landlord-overview-metric__value">{data.response_rate}</p>
            </article>
          </li>
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">
                Average Response Time
              </p>
              <p className="landlord-overview-metric__value">
                {data.average_response_time}
              </p>
            </article>
          </li>
        </ul>

        <div className="landlord-overview-summary">
          <p className="landlord-overview-summary__label">Summary</p>
          <p className="landlord-overview-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

function LandlordRiskSummarySection({ data }) {
  const riskHint = getRiskLevelHint(data.trust_score);
  const scoreTone = trustScoreTone(data.trust_score);

  return (
    <section
      id="landlord-risk-summary"
      className="landlord-risk"
      aria-labelledby="landlord-risk-heading"
    >
      <header className="landlord-risk__header">
        <h2 id="landlord-risk-heading" className="landlord-risk__title">
          Landlord Risk Summary
        </h2>
        <p className="landlord-risk__subtitle">
          Combined mock risk assessment from reputation, complaints, history, and
          verification — not connected to live risk scoring.
        </p>
      </header>

      <div className="card landlord-risk-panel">
        <div className="landlord-risk-badge-wrap" role="status">
          <p
            className={`landlord-overview-hint landlord-overview-hint--${riskHint.tone} landlord-risk-badge`}
          >
            {riskHint.label}
          </p>
        </div>

        <div className="landlord-overview-trust landlord-risk-trust">
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
          <div className="landlord-overview-detail landlord-risk-overall">
            <p className="landlord-overview-detail__label">Overall Risk</p>
            <p className="landlord-overview-detail__value">{data.overall_risk}</p>
          </div>
        </div>

        <ul
          className="landlord-overview-metrics landlord-risk-metrics"
          aria-label="Risk level breakdown"
        >
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Complaint Level</p>
              <p className="landlord-overview-metric__value">
                {data.complaint_level}
              </p>
            </article>
          </li>
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">
                Rental History Level
              </p>
              <p className="landlord-overview-metric__value">
                {data.rental_history_level}
              </p>
            </article>
          </li>
          <li>
            <article className="landlord-overview-metric">
              <p className="landlord-overview-metric__label">Verification Level</p>
              <p className="landlord-overview-metric__value">
                {data.verification_level}
              </p>
            </article>
          </li>
        </ul>

        <div className="landlord-risk-recommendation">
          <p className="landlord-overview-summary__label">Recommendation</p>
          <p className="landlord-overview-summary__text">{data.recommendation}</p>
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
      <RentalHistorySignalsSection data={mockRentalHistory} />
      <LandlordVerificationSignalsSection data={mockVerificationSignals} />
      <LandlordRiskSummarySection data={mockRiskSummary} />
    </div>
  );
}
