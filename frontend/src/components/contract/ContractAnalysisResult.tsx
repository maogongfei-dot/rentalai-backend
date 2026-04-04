import { LegalCompliancePanel } from "@/components/legal/LegalCompliancePanel";

export type ContractAnalysisResultProps = {
  /** API `result` object, or full `{ ok, result }` response. */
  result?: any;
};

/**
 * Contract analysis summary + legal compliance (Phase 4 API shape).
 */
export function ContractAnalysisResult({ result: payload }: ContractAnalysisResultProps) {
  if (!payload) return null;

  const result = payload?.result != null ? payload.result : payload;

  console.log("FULL RESULT:", payload);
  console.log("LEGAL FIELD:", result?.legal_compliance);

  const legalCompliance =
    result?.legal_compliance ||
    result?.data?.legal_compliance ||
    result?.result?.legal_compliance;

  return (
    <div className="contract-analysis-result-react">
      <section className="contract-result-card-block" aria-labelledby="ca-overall-conclusion">
        <header className="contract-result-card-head">
          <h2 id="ca-overall-conclusion" className="contract-result-block-title">
            <span className="contract-result-block-en">Overall Conclusion</span>
          </h2>
        </header>
        <div className="contract-result-card-body">
          <p className="contract-result-text">
            {String(result?.summary_view?.overall_conclusion ?? "").trim() || "—"}
          </p>
        </div>
      </section>

      <section className="contract-result-card-block" aria-labelledby="ca-key-risk-summary">
        <header className="contract-result-card-head">
          <h2 id="ca-key-risk-summary" className="contract-result-block-title">
            <span className="contract-result-block-en">Key Risk Summary</span>
          </h2>
        </header>
        <div className="contract-result-card-body">
          <p className="contract-result-text">
            {String(result?.summary_view?.key_risk_summary ?? "").trim() || "—"}
          </p>
        </div>
      </section>

      <LegalCompliancePanel legalCompliance={legalCompliance} />
    </div>
  );
}
