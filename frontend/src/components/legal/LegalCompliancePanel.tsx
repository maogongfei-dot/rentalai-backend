import { LegalRuleCard } from "./LegalRuleCard";

function safeObject(v: unknown): Record<string, any> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, any>) : {};
}

function normalizeRules(rules: unknown): any[] {
  return Array.isArray(rules) ? rules : [];
}

export type LegalCompliancePanelProps = {
  legalCompliance: any;
};

/**
 * Legal compliance summary + rules (backend `legal_compliance` payload).
 */
export function LegalCompliancePanel({ legalCompliance }: LegalCompliancePanelProps) {
  const lc = legalCompliance;

  if (lc == null || typeof lc !== "object") {
    return (
      <section className="legal-compliance-panel" aria-labelledby="legal-compliance-heading">
        <h3 id="legal-compliance-heading" className="contract-result-block-title">
          <span className="contract-result-block-en">Legal Compliance Check</span>
        </h3>
        <p className="contract-result-muted">No detailed legal compliance result is available yet.</p>
      </section>
    );
  }

  const overall = safeObject(lc.overall);
  const rules = normalizeRules(lc.rules);

  const status = String(overall.overall_legal_status ?? "").trim();
  const risk = String(overall.overall_risk_level ?? "").trim();
  const summary = String(overall.summary_plain ?? "").trim();
  const disclaimer = String(overall.disclaimer ?? "").trim();

  const showOverall = Boolean(status || risk || summary);

  return (
    <section className="legal-compliance-panel" aria-labelledby="legal-compliance-heading">
      <h3 id="legal-compliance-heading" className="contract-result-block-title">
        <span className="contract-result-block-en">Legal Compliance Check</span>
      </h3>

      {showOverall ? (
        <div className="legal-compliance-overall">
          {status ? (
            <p className="contract-result-kv">
              <span className="contract-result-kv-label">Overall legal status</span>
              {status}
            </p>
          ) : null}
          {risk ? (
            <p className="contract-result-kv">
              <span className="contract-result-kv-label">Overall risk level</span>
              {risk}
            </p>
          ) : null}
          {summary ? <p className="contract-result-text">{summary}</p> : null}
        </div>
      ) : null}

      {disclaimer ? (
        <div className="legal-compliance-disclaimer" role="note">
          {disclaimer}
        </div>
      ) : null}

      {rules.length === 0 ? (
        <p className="contract-result-muted legal-compliance-empty-hint">
          No detailed legal compliance result is available yet.
        </p>
      ) : (
        <div className="contract-result-subcard-stack legal-compliance-rules">
          {rules.map((rule, idx) => (
            <LegalRuleCard key={String(rule?.rule_id ?? idx)} rule={rule} />
          ))}
        </div>
      )}
    </section>
  );
}
