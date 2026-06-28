import "./LandlordCenter.css";

/**
 * Landlord Center — mock reputation preview (frontend only, no API).
 * Phase 8: landlord trust, complaints, rental history, and verification signals.
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

const mockLandlordComplaintSignals = {
  complaint_count: 1,
  complaint_types: ["Delayed repairs", "Deposit dispute"],
  complaint_severity: "Medium",
  unresolved_complaints: 1,
  recent_complaint:
    "Tenant reported delayed repair response within the last 6 months.",
  summary:
    "There are some complaint signals, mainly around repair response and deposit handling. Renters should review contract terms and communication records carefully.",
};

const mockLandlordRentalHistory = {
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

const mockLandlordVerificationSignals = {
  identity_verified: true,
  email_verified: true,
  phone_verified: true,
  ownership_verification: "Not verified",
  response_rate: "82%",
  average_response_time: "6 hours",
  summary:
    "This landlord has basic identity and contact verification, but property ownership has not yet been verified.",
};

const mockLandlordRiskSummary = {
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

const mockLandlordTimeline = [
  { date: "2022", event: "Started letting properties", type: "info" },
  { date: "2023", event: "Identity verified", type: "success" },
  { date: "2024", event: "First tenant complaint recorded", type: "warning" },
  { date: "2025", event: "Trust score improved", type: "success" },
];

const MOCK_LANDLORD_TIMELINE_SUMMARY =
  "Timeline provides a simple overview of important landlord reputation events.";

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

function buildLandlordDashboardData(
  overview,
  complaint,
  rentalHistory,
  riskSummary,
) {
  return {
    trustScore: riskSummary.trust_score,
    riskLevel: riskSummary.overall_risk,
    riskHint: getRiskLevelHint(riskSummary.trust_score),
    complaintLevel: riskSummary.complaint_level,
    rentalHistoryLevel: riskSummary.rental_history_level,
    verificationStatus: overview.verification_status,
    verificationLevel: riskSummary.verification_level,
    yearsActive: rentalHistory.years_active,
    estimatedTenancies: rentalHistory.estimated_tenancies,
    complaintCount: complaint.complaint_count,
    trustHint: getTrustScoreHint(riskSummary.trust_score),
  };
}

function getTimelineItemMeta(type) {
  const meta = {
    success: { icon: "✓", tone: "success", label: "Success event" },
    warning: { icon: "!", tone: "warning", label: "Warning event" },
    info: { icon: "i", tone: "info", label: "Info event" },
  };
  return meta[type] ?? meta.info;
}

function sortTimelineByDate(items) {
  return [...items].sort(
    (a, b) => Number.parseInt(a.date, 10) - Number.parseInt(b.date, 10),
  );
}

function LandlordSection({ id, title, subtitle, children }) {
  return (
    <section
      id={id}
      className="landlord-section"
      aria-labelledby={`${id}-heading`}
    >
      <header className="landlord-section__header">
        <h2 id={`${id}-heading`} className="landlord-section__title">
          {title}
        </h2>
        {subtitle ? (
          <p className="landlord-section__subtitle">{subtitle}</p>
        ) : null}
      </header>
      {children}
    </section>
  );
}

function LandlordPanel({ children, className = "" }) {
  return (
    <div className={`card landlord-panel${className ? ` ${className}` : ""}`}>
      {children}
    </div>
  );
}

function LandlordHintBadge({ label, tone = "mid" }) {
  return (
    <p className={`landlord-badge landlord-badge--${tone}`} role="status">
      {label}
    </p>
  );
}

function LandlordHintRow({ children, ...props }) {
  return (
    <div className="landlord-hint-row" {...props}>
      {children}
    </div>
  );
}

function LandlordMetricGrid({ label, children, className = "" }) {
  return (
    <ul
      className={`landlord-metrics${className ? ` ${className}` : ""}`}
      aria-label={label}
    >
      {children}
    </ul>
  );
}

function LandlordMetric({ label, value, variant }) {
  return (
    <li>
      <article
        className={`landlord-metric${variant ? ` landlord-metric--${variant}` : ""}`}
      >
        <p className="landlord-field__label">{label}</p>
        <p className="landlord-field__value landlord-field__value--metric">
          {value}
        </p>
      </article>
    </li>
  );
}

function LandlordDetailGrid({ children }) {
  return <div className="landlord-details">{children}</div>;
}

function LandlordDetail({ label, value, badge, badgeTone = "info" }) {
  return (
    <div className="landlord-detail">
      <p className="landlord-field__label">{label}</p>
      {badge ? (
        <p className={`landlord-badge landlord-badge--${badgeTone}`}>{value}</p>
      ) : (
        <p className="landlord-field__value">{value}</p>
      )}
    </div>
  );
}

function LandlordSummary({ label = "Summary", text, highlight = false }) {
  return (
    <div
      className={`landlord-summary${highlight ? " landlord-summary--highlight" : ""}`}
    >
      <p className="landlord-field__label landlord-field__label--summary">
        {label}
      </p>
      <p className="landlord-summary__text">{text}</p>
    </div>
  );
}

function TrustScoreBlock({ score, hintLabel, hintTone }) {
  const scoreTone = trustScoreTone(score);

  return (
    <div className="landlord-trust-block">
      <div className="landlord-trust-block__main">
        <p className="landlord-field__label">Trust Score</p>
        <p
          className={`landlord-trust-block__value landlord-trust-block__value--${scoreTone}`}
          aria-label={`Trust score ${score} out of 100`}
        >
          <span className="landlord-trust-block__number">{score}</span>
          <span className="landlord-trust-block__max">/ 100</span>
        </p>
      </div>
      {hintLabel ? (
        <LandlordHintBadge label={hintLabel} tone={hintTone} />
      ) : null}
    </div>
  );
}

function LandlordTagList({ items, emptyLabel = "None listed" }) {
  if (!items?.length) {
    return <p className="landlord-empty">{emptyLabel}</p>;
  }

  return (
    <ul className="landlord-tag-list">
      {items.map((item) => (
        <li key={item}>
          <span className="landlord-badge landlord-badge--mid landlord-badge--tag">
            {item}
          </span>
        </li>
      ))}
    </ul>
  );
}

function DashboardSummaryCard({
  label,
  value,
  detail,
  tone = "neutral",
  badge = false,
}) {
  return (
    <article
      className={`card landlord-dashboard-card landlord-dashboard-card--${tone}`}
    >
      <p className="landlord-field__label">{label}</p>
      {badge ? (
        <LandlordHintBadge label={value} tone={tone} />
      ) : (
        <>
          <p className="landlord-dashboard-card__value">{value}</p>
          {detail ? (
            <p className="landlord-dashboard-card__detail">{detail}</p>
          ) : null}
        </>
      )}
    </article>
  );
}

function LandlordReputationDashboard({ data }) {
  const trustTone = trustScoreTone(data.trustScore);

  const detailMetrics = [
    { label: "Overall Trust Score", value: String(data.trustScore) },
    { label: "Overall Risk Level", value: data.riskLevel },
    { label: "Complaint Level", value: data.complaintLevel },
    { label: "Rental History", value: data.rentalHistoryLevel },
    { label: "Verification Status", value: data.verificationStatus },
    { label: "Years Active", value: String(data.yearsActive) },
    { label: "Estimated Tenancies", value: String(data.estimatedTenancies) },
  ];

  return (
    <LandlordSection
      id="landlord-reputation-dashboard"
      title="Landlord Reputation Dashboard"
      subtitle="Combined mock reputation overview from trust, risk, complaints, history, and verification signals."
    >
      <LandlordPanel>
        <ul
          className="landlord-dashboard-cards"
          aria-label="Summary cards"
        >
          <li>
            <DashboardSummaryCard
              label="Trust Score"
              value={data.trustScore}
              detail={`${data.trustHint.label} · / 100`}
              tone={trustTone}
            />
          </li>
          <li>
            <DashboardSummaryCard
              label="Risk Level"
              value={data.riskHint.label}
              tone={data.riskHint.tone}
              badge
            />
          </li>
          <li>
            <DashboardSummaryCard
              label="Verification"
              value={data.verificationStatus}
              detail={`Level: ${data.verificationLevel}`}
              tone="info"
            />
          </li>
          <li>
            <DashboardSummaryCard
              label="Complaints"
              value={data.complaintCount}
              detail={`${data.complaintLevel} level`}
              tone={data.complaintCount > 0 ? "mid" : "high"}
            />
          </li>
        </ul>

        <LandlordMetricGrid
          label="Reputation dashboard details"
          className="landlord-metrics--dashboard"
        >
          {detailMetrics.map((metric) => (
            <LandlordMetric
              key={metric.label}
              label={metric.label}
              value={metric.value}
            />
          ))}
        </LandlordMetricGrid>
      </LandlordPanel>
    </LandlordSection>
  );
}

function LandlordReputationOverviewSection({ data }) {
  const hint = getTrustScoreHint(data.trust_score);

  return (
    <LandlordSection
      id="landlord-reputation-overview"
      title="Landlord Reputation Overview"
      subtitle="Mock landlord trust signals for preview — not connected to live reputation or complaint data."
    >
      <LandlordPanel>
        <div className="landlord-identity">
          <p className="landlord-field__label">Landlord Name</p>
          <p className="landlord-identity__name">{data.landlord_name}</p>
        </div>

        <TrustScoreBlock
          score={data.trust_score}
          hintLabel={hint.label}
          hintTone={hint.tone}
        />

        <LandlordMetricGrid label="Landlord metrics">
          <LandlordMetric
            label="Total Properties"
            value={data.total_properties}
          />
          <LandlordMetric
            label="Complaint Count"
            value={data.complaint_count}
            variant={data.complaint_count > 0 ? "caution" : undefined}
          />
        </LandlordMetricGrid>

        <LandlordDetailGrid>
          <LandlordDetail label="Response Speed" value={data.response_speed} />
          <LandlordDetail
            label="Verification Status"
            value={data.verification_status}
            badge
            badgeTone="info"
          />
        </LandlordDetailGrid>

        <LandlordSummary text={data.summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

function ComplaintSignalsSection({ data }) {
  const hint = getComplaintRiskHint(data.unresolved_complaints);

  return (
    <LandlordSection
      id="complaint-signals"
      title="Complaint Signals"
      subtitle="Mock complaint and dispute signals for preview — not connected to live complaint records."
    >
      <LandlordPanel>
        <LandlordHintRow>
          <LandlordHintBadge label={hint.label} tone={hint.tone} />
        </LandlordHintRow>

        <LandlordMetricGrid label="Complaint metrics">
          <LandlordMetric
            label="Complaint Count"
            value={data.complaint_count}
            variant={data.complaint_count > 0 ? "caution" : undefined}
          />
          <LandlordMetric
            label="Unresolved Complaints"
            value={data.unresolved_complaints}
            variant={data.unresolved_complaints > 0 ? "caution" : undefined}
          />
        </LandlordMetricGrid>

        <div className="landlord-detail landlord-detail--accent">
          <p className="landlord-field__label">Complaint Types</p>
          <LandlordTagList items={data.complaint_types} />
        </div>

        <LandlordDetail
          label="Complaint Severity"
          value={data.complaint_severity}
          badge
          badgeTone="mid"
        />

        <LandlordDetail label="Recent Complaint" value={data.recent_complaint} />

        <LandlordSummary text={data.summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

function RentalHistorySignalsSection({ data }) {
  const hint = getRentalHistoryHint(data.years_active);

  return (
    <LandlordSection
      id="rental-history-signals"
      title="Rental History Signals"
      subtitle="Mock rental history and tenancy patterns for preview — not connected to live tenancy records."
    >
      <LandlordPanel>
        <LandlordHintRow>
          <LandlordHintBadge label={hint.label} tone={hint.tone} />
        </LandlordHintRow>

        <LandlordMetricGrid label="Rental history metrics">
          <LandlordMetric label="Years Active" value={data.years_active} />
          <LandlordMetric
            label="Estimated Tenancies"
            value={data.estimated_tenancies}
          />
        </LandlordMetricGrid>

        <LandlordDetailGrid>
          <LandlordDetail
            label="Repeat Tenant Signal"
            value={data.repeat_tenant_signal}
          />
          <LandlordDetail
            label="Average Tenancy Length"
            value={data.average_tenancy_length}
          />
          <LandlordDetail
            label="Rent Increase Signal"
            value={data.rent_increase_signal}
          />
          <LandlordDetail
            label="Property Maintenance Signal"
            value={data.property_maintenance_signal}
          />
        </LandlordDetailGrid>

        <LandlordSummary text={data.summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

function LandlordVerificationSignalsSection({ data }) {
  const hints = getVerificationHints(data);

  return (
    <LandlordSection
      id="landlord-verification-signals"
      title="Landlord Verification Signals"
      subtitle="Mock identity and contact verification signals for preview — not connected to live verification services."
    >
      <LandlordPanel>
        <LandlordHintRow role="status">
          {hints.map((hint) => (
            <LandlordHintBadge
              key={hint.label}
              label={hint.label}
              tone={hint.tone}
            />
          ))}
        </LandlordHintRow>

        <LandlordDetailGrid>
          <LandlordDetail
            label="Identity Verified"
            value={data.identity_verified ? "Verified" : "Not verified"}
            badge
            badgeTone={data.identity_verified ? "high" : "mid"}
          />
          <LandlordDetail
            label="Email Verified"
            value={data.email_verified ? "Verified" : "Not verified"}
            badge
            badgeTone={data.email_verified ? "high" : "mid"}
          />
          <LandlordDetail
            label="Phone Verified"
            value={data.phone_verified ? "Verified" : "Not verified"}
            badge
            badgeTone={data.phone_verified ? "high" : "mid"}
          />
          <LandlordDetail
            label="Ownership Verification"
            value={data.ownership_verification}
            badge
            badgeTone={
              data.ownership_verification === "Verified" ? "high" : "mid"
            }
          />
        </LandlordDetailGrid>

        <LandlordMetricGrid label="Verification response metrics">
          <LandlordMetric label="Response Rate" value={data.response_rate} />
          <LandlordMetric
            label="Average Response Time"
            value={data.average_response_time}
          />
        </LandlordMetricGrid>

        <LandlordSummary text={data.summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

function LandlordRiskSummarySection({ data }) {
  const riskHint = getRiskLevelHint(data.trust_score);
  const trustHint = getTrustScoreHint(data.trust_score);

  return (
    <LandlordSection
      id="landlord-risk-summary"
      title="Landlord Risk Summary"
      subtitle="Combined mock risk assessment from reputation, complaints, history, and verification — not connected to live risk scoring."
    >
      <LandlordPanel>
        <LandlordHintRow role="status">
          <LandlordHintBadge label={riskHint.label} tone={riskHint.tone} />
        </LandlordHintRow>

        <div className="landlord-trust-block landlord-trust-block--split">
          <TrustScoreBlock
            score={data.trust_score}
            hintLabel={trustHint.label}
            hintTone={trustHint.tone}
          />
          <LandlordDetail label="Overall Risk" value={data.overall_risk} />
        </div>

        <LandlordMetricGrid
          label="Risk level breakdown"
          className="landlord-metrics--risk"
        >
          <LandlordMetric label="Complaint Level" value={data.complaint_level} />
          <LandlordMetric
            label="Rental History Level"
            value={data.rental_history_level}
          />
          <LandlordMetric
            label="Verification Level"
            value={data.verification_level}
          />
        </LandlordMetricGrid>

        <LandlordSummary
          label="Recommendation"
          text={data.recommendation}
          highlight
        />
        <LandlordSummary text={data.summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

function LandlordReputationTimelineSection({ items, summary }) {
  const sortedItems = sortTimelineByDate(items);

  return (
    <LandlordSection
      id="landlord-reputation-timeline"
      title="Landlord Reputation Timeline"
      subtitle="Mock reputation milestones for preview — not connected to live event records."
    >
      <LandlordPanel>
        <ol className="landlord-timeline-list" aria-label="Timeline">
          {sortedItems.map((item) => {
            const meta = getTimelineItemMeta(item.type);

            return (
              <li key={`${item.date}-${item.event}`}>
                <article
                  className={`landlord-timeline-item landlord-timeline-item--${meta.tone}`}
                >
                  <span
                    className="landlord-timeline-item__icon"
                    aria-label={meta.label}
                    title={meta.label}
                  >
                    {meta.icon}
                  </span>
                  <div className="landlord-timeline-item__body">
                    <p className="landlord-field__label">{item.date}</p>
                    <p className="landlord-field__value">{item.event}</p>
                  </div>
                </article>
              </li>
            );
          })}
        </ol>

        <LandlordSummary text={summary} />
      </LandlordPanel>
    </LandlordSection>
  );
}

export default function LandlordCenter() {
  const dashboardData = buildLandlordDashboardData(
    mockLandlordOverview,
    mockLandlordComplaintSignals,
    mockLandlordRentalHistory,
    mockLandlordRiskSummary,
  );

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

      <LandlordReputationDashboard data={dashboardData} />
      <LandlordReputationOverviewSection data={mockLandlordOverview} />
      <ComplaintSignalsSection data={mockLandlordComplaintSignals} />
      <RentalHistorySignalsSection data={mockLandlordRentalHistory} />
      <LandlordVerificationSignalsSection data={mockLandlordVerificationSignals} />
      <LandlordRiskSummarySection data={mockLandlordRiskSummary} />
      <LandlordReputationTimelineSection
        items={mockLandlordTimeline}
        summary={MOCK_LANDLORD_TIMELINE_SUMMARY}
      />
    </div>
  );
}
