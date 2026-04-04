function formatConfidence(value: unknown): string {
  if (value == null || value === "") return "";
  const n = Number(value);
  if (Number.isFinite(n)) {
    if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
    return String(n);
  }
  return "";
}

function safeStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => String(x ?? "").trim()).filter(Boolean);
}

export type LegalRuleCardProps = {
  rule: any;
};

/**
 * Single legal rule row (aligned with backend rule output shape).
 */
export function LegalRuleCard({ rule }: LegalRuleCardProps) {
  const r = rule && typeof rule === "object" ? rule : {};
  const title = String(r.title ?? "").trim() || "—";
  const legalStatus = String(r.legal_status ?? "").trim();
  const riskLevel = String(r.risk_level ?? "").trim();
  const explanation = String(r.explanation_plain ?? "").trim();
  const redFlags = safeStringArray(r.matched_red_flags);
  const keyPoints = safeStringArray(r.matched_key_points);
  const conf = formatConfidence(r.confidence);

  return (
    <article className="legal-rule-card contract-result-subcard">
      <div className="legal-rule-card__head contract-result-subcard-head">
        <strong>{title}</strong>
        <div className="contract-result-subcard-badges">
          {legalStatus ? (
            <span className="contract-result-pill contract-result-pill--muted">{legalStatus}</span>
          ) : null}
          {riskLevel ? (
            <span className="contract-result-pill contract-result-pill--severity">{riskLevel}</span>
          ) : null}
        </div>
      </div>
      {explanation ? (
        <p className="contract-result-text legal-rule-card__explain">{explanation}</p>
      ) : null}
      {redFlags.length > 0 ? (
        <section className="legal-rule-card__section" aria-label="Red flags">
          <h4 className="legal-rule-card__section-title">Red flags</h4>
          <ul className="contract-result-list contract-result-list--spaced">
            {redFlags.map((line, i) => (
              <li key={`rf-${i}`}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {keyPoints.length > 0 ? (
        <section className="legal-rule-card__section" aria-label="Key points">
          <h4 className="legal-rule-card__section-title">Key points</h4>
          <ul className="contract-result-list contract-result-list--spaced">
            {keyPoints.map((line, i) => (
              <li key={`kp-${i}`}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {conf ? (
        <p className="contract-result-muted legal-rule-card__confidence">
          <span className="contract-result-quick-label">Confidence</span> {conf}
        </p>
      ) : null}
    </article>
  );
}
