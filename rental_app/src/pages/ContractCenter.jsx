import { useRef, useState } from "react";
import {
  mockContractChatExamples,
  mockContractRisks,
  mockContractSummary,
  mockMissingClauses,
} from "../data/contractMockData.js";
import "./ContractCenter.css";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".pdf", ".doc", ".docx"];

const REVIEW_STATUS = {
  NOT_STARTED: "Not started",
  READY: "Ready for review",
  COMPLETED: "Mock review completed",
};

const SECTION_NAV = [
  { id: "upload-contract", label: "Upload" },
  { id: "risk-detection", label: "Risks" },
  { id: "missing-clauses", label: "Clauses" },
  { id: "contract-ai-chat", label: "AI Chat" },
];

function getFileExtension(name) {
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index).toLowerCase() : "";
}

function isAcceptedContractFile(file) {
  const ext = getFileExtension(file.name);
  return ACCEPTED_EXTENSIONS.includes(ext);
}

function ContractSection({ id, step, title, subtitle, children }) {
  return (
    <section
      id={id}
      className="contract-section"
      aria-labelledby={`${id}-heading`}
    >
      <header className="contract-section__header">
        <span className="contract-section__step" aria-hidden="true">
          {step}
        </span>
        <div className="contract-section__titles">
          <h2 id={`${id}-heading`} className="contract-section__title">
            {title}
          </h2>
          {subtitle ? (
            <p className="contract-section__subtitle">{subtitle}</p>
          ) : null}
        </div>
      </header>
      {children}
    </section>
  );
}

function ContractSummary({ selectedFile, risks, clauses, reviewStatus }) {
  const items = mockContractSummary({
    selectedFile,
    risks,
    clauses,
    reviewStatus,
  });

  return (
    <section className="contract-summary" aria-label="Contract summary">
      <ul className="contract-summary__grid">
        {items.map((item) => (
          <li key={item.id}>
            <article
              className={`card contract-summary-card contract-summary-card--${item.tone}`}
            >
              <p className="contract-summary-card__label">{item.label}</p>
              <p className="contract-summary-card__value" title={item.value}>
                {item.value}
              </p>
              <p className="contract-summary-card__detail">{item.detail}</p>
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}

function UploadContractSection({
  selectedFile,
  fileError,
  inputRef,
  onChooseClick,
  onFileChange,
  onClearFile,
  onStartMockReview,
}) {
  return (
    <ContractSection
      id="upload-contract"
      step="01"
      title="Upload Contract"
      subtitle="Select a tenancy agreement for mock AI review (no server upload)."
    >
      <div className="card contract-panel">
        <p className="contract-panel__label">Tenancy agreement</p>

        <div
          className={`contract-upload__dropzone${selectedFile ? " contract-upload__dropzone--ready" : ""}`}
        >
          <input
            ref={inputRef}
            id="contract-file-input"
            type="file"
            className="contract-upload__input"
            accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={onFileChange}
          />

          {!selectedFile ? (
            <>
              <p className="contract-upload__hint">
                Choose a file to begin mock contract review.
              </p>
              <button
                type="button"
                className="contract-btn contract-btn--secondary"
                onClick={onChooseClick}
              >
                Choose file
              </button>
            </>
          ) : (
            <>
              <p className="contract-upload__filename" title={selectedFile.name}>
                {selectedFile.name}
              </p>
              <span className="contract-badge contract-badge--success">
                Ready for review
              </span>
              <button
                type="button"
                className="contract-upload__clear-btn"
                onClick={onClearFile}
              >
                Remove file
              </button>
            </>
          )}
        </div>

        <ul className="contract-upload__meta">
          <li>Accepted formats: PDF, DOC, DOCX</li>
          <li>Max file size: 10MB</li>
        </ul>

        {fileError ? (
          <p className="contract-upload__error" role="alert">
            {fileError}
          </p>
        ) : null}

        <div className="contract-panel__actions">
          <button
            type="button"
            className="contract-btn contract-btn--primary"
            disabled={!selectedFile}
            onClick={onStartMockReview}
          >
            Start mock review
          </button>
        </div>
      </div>
    </ContractSection>
  );
}

function riskLevelLabel(level) {
  const labels = { low: "Low risk", medium: "Medium risk", high: "High risk" };
  return labels[level] ?? level;
}

function RiskLevelBadge({ level }) {
  return (
    <span className={`contract-badge contract-badge--risk-${level}`}>
      {riskLevelLabel(level)}
    </span>
  );
}

function ContractRiskCard({ risk }) {
  return (
    <li className="card contract-item-card">
      <div className="contract-item-card__header">
        <h3 className="contract-item-card__title">{risk.clause_title}</h3>
        <RiskLevelBadge level={risk.risk_level} />
      </div>
      <p className="contract-item-card__block">
        <span className="contract-item-card__label">Issue</span>
        {risk.issue}
      </p>
      <p className="contract-item-card__block">
        <span className="contract-item-card__label">Explanation</span>
        {risk.explanation}
      </p>
      <p className="contract-item-card__callout">
        <span className="contract-item-card__label">Suggested action</span>
        {risk.suggested_action}
      </p>
    </li>
  );
}

function RiskDetectionSection({ risks }) {
  const highCount = risks.filter((r) => r.risk_level === "high").length;
  const mediumCount = risks.filter((r) => r.risk_level === "medium").length;

  return (
    <ContractSection
      id="risk-detection"
      step="02"
      title="Risk Detection"
      subtitle={`${risks.length} issue${risks.length === 1 ? "" : "s"} · ${highCount} high · ${mediumCount} medium · mock data`}
    >
      <ul className="contract-item-list">
        {risks.map((risk) => (
          <ContractRiskCard key={risk.id} risk={risk} />
        ))}
      </ul>
    </ContractSection>
  );
}

function clauseStatusLabel(status) {
  const labels = { missing: "Missing", weak: "Weak", unclear: "Unclear" };
  return labels[status] ?? status;
}

function clauseImportanceLabel(level) {
  const labels = { low: "Low", medium: "Medium", high: "High" };
  return labels[level] ?? level;
}

function ClauseStatusBadge({ status }) {
  return (
    <span className={`contract-badge contract-badge--clause-${status}`}>
      {clauseStatusLabel(status)}
    </span>
  );
}

function ClauseImportanceBadge({ importance }) {
  return (
    <span className={`contract-badge contract-badge--importance-${importance}`}>
      {clauseImportanceLabel(importance)} importance
    </span>
  );
}

function MissingClauseCard({ clause }) {
  return (
    <li className="card contract-item-card">
      <div className="contract-item-card__header">
        <h3 className="contract-item-card__title">{clause.clause_name}</h3>
        <div className="contract-item-card__badges">
          <ClauseStatusBadge status={clause.status} />
          <ClauseImportanceBadge importance={clause.importance} />
        </div>
      </div>
      <p className="contract-item-card__block">
        <span className="contract-item-card__label">Explanation</span>
        {clause.explanation}
      </p>
      <p className="contract-item-card__callout">
        <span className="contract-item-card__label">Suggested fix</span>
        {clause.suggested_fix}
      </p>
    </li>
  );
}

function MissingClausesSection({ clauses }) {
  const missingCount = clauses.filter((c) => c.status === "missing").length;
  const highCount = clauses.filter((c) => c.importance === "high").length;

  return (
    <ContractSection
      id="missing-clauses"
      step="03"
      title="Missing Clauses"
      subtitle={`${clauses.length} item${clauses.length === 1 ? "" : "s"} · ${missingCount} missing · ${highCount} high importance · mock data`}
    >
      <ul className="contract-item-list">
        {clauses.map((clause) => (
          <MissingClauseCard key={clause.id} clause={clause} />
        ))}
      </ul>
    </ContractSection>
  );
}

function ContractAiChatSection({
  contractQuestion,
  lastAskedQuestion,
  contractAnswer,
  onQuestionChange,
  onAsk,
  onClear,
}) {
  return (
    <ContractSection
      id="contract-ai-chat"
      step="04"
      title="Contract AI Chat"
      subtitle="Ask about your tenancy agreement · mock responses only"
    >
      <div className="card contract-panel">
        <form className="contract-chat__form" onSubmit={onAsk}>
          <label className="contract-panel__label" htmlFor="contract-chat-input">
            Your question
          </label>
          <div className="contract-chat__input-row">
            <input
              id="contract-chat-input"
              type="text"
              className="contract-chat__input"
              value={contractQuestion}
              onChange={onQuestionChange}
              placeholder={mockContractChatExamples.placeholder}
              autoComplete="off"
            />
            <button
              type="submit"
              className="contract-btn contract-btn--primary"
              disabled={!contractQuestion.trim()}
            >
              Ask
            </button>
          </div>
        </form>

        <div
          className="contract-chat__responses"
          aria-live="polite"
          aria-label="Contract AI responses"
        >
          {!contractAnswer ? (
            <p className="contract-chat__empty">
              {mockContractChatExamples.emptyMessage}
            </p>
          ) : (
            <ul className="contract-chat__list">
              <li className="contract-chat__exchange">
                <p className="contract-chat__question">
                  <span className="contract-badge contract-badge--tag">You</span>
                  {lastAskedQuestion}
                </p>
                <p className="contract-chat__answer">
                  <span className="contract-badge contract-badge--tag-ai">
                    RentalAI
                  </span>
                  {contractAnswer}
                </p>
              </li>
            </ul>
          )}
        </div>

        {contractAnswer ? (
          <button
            type="button"
            className="contract-upload__clear-btn contract-chat__clear-btn"
            onClick={onClear}
          >
            Clear question
          </button>
        ) : null}
      </div>
    </ContractSection>
  );
}

export default function ContractCenter() {
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [reviewStatus, setReviewStatus] = useState(REVIEW_STATUS.NOT_STARTED);
  const [contractQuestion, setContractQuestion] = useState("");
  const [lastAskedQuestion, setLastAskedQuestion] = useState("");
  const [contractAnswer, setContractAnswer] = useState("");

  function resetFileInput() {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleChooseFileClick() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    setFileError("");

    if (!file) {
      setSelectedFile(null);
      setReviewStatus(REVIEW_STATUS.NOT_STARTED);
      return;
    }

    if (!isAcceptedContractFile(file)) {
      setSelectedFile(null);
      setReviewStatus(REVIEW_STATUS.NOT_STARTED);
      setFileError("Please choose a PDF, DOC, or DOCX file.");
      resetFileInput();
      return;
    }

    if (file.size > MAX_FILE_BYTES) {
      setSelectedFile(null);
      setReviewStatus(REVIEW_STATUS.NOT_STARTED);
      setFileError("File is too large. Maximum size is 10MB.");
      resetFileInput();
      return;
    }

    setSelectedFile(file);
    setReviewStatus(REVIEW_STATUS.READY);
  }

  function handleClearFile() {
    setSelectedFile(null);
    setFileError("");
    setReviewStatus(REVIEW_STATUS.NOT_STARTED);
    resetFileInput();
  }

  function handleStartMockReview() {
    if (!selectedFile) return;

    console.log("Start mock contract review:", {
      name: selectedFile.name,
      size: selectedFile.size,
      type: selectedFile.type,
    });

    setReviewStatus(REVIEW_STATUS.COMPLETED);
  }

  function handleAskContractQuestion(event) {
    event.preventDefault();
    const trimmed = contractQuestion.trim();
    if (!trimmed) return;

    setLastAskedQuestion(trimmed);
    setContractAnswer(mockContractChatExamples.defaultReply);
  }

  function handleClearContractQuestion() {
    setContractQuestion("");
    setLastAskedQuestion("");
    setContractAnswer("");
  }

  return (
    <div className="page-shell contract-center">
      <header className="contract-hero">
        <div className="contract-hero__top">
          <p className="contract-hero__eyebrow">RentalAI Contract Hub</p>
          <span className="contract-hero__pill">Mock preview</span>
        </div>
        <h1 className="contract-hero__title">Contract Analysis Center</h1>
        <p className="contract-hero__subtitle">
          Review tenancy agreements, surface rental risks, check missing clauses,
          and ask contract questions — all in one workspace.
        </p>
        <nav className="contract-hero__nav" aria-label="Contract sections">
          <ul className="contract-hero__nav-list">
            {SECTION_NAV.map((item) => (
              <li key={item.id}>
                <a className="contract-hero__nav-link" href={`#${item.id}`}>
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <ContractSummary
        selectedFile={selectedFile}
        risks={mockContractRisks}
        clauses={mockMissingClauses}
        reviewStatus={reviewStatus}
      />

      <main className="contract-main">
        <UploadContractSection
          selectedFile={selectedFile}
          fileError={fileError}
          inputRef={fileInputRef}
          onChooseClick={handleChooseFileClick}
          onFileChange={handleFileChange}
          onClearFile={handleClearFile}
          onStartMockReview={handleStartMockReview}
        />
        <RiskDetectionSection risks={mockContractRisks} />
        <MissingClausesSection clauses={mockMissingClauses} />
        <ContractAiChatSection
          contractQuestion={contractQuestion}
          lastAskedQuestion={lastAskedQuestion}
          contractAnswer={contractAnswer}
          onQuestionChange={(event) => setContractQuestion(event.target.value)}
          onAsk={handleAskContractQuestion}
          onClear={handleClearContractQuestion}
        />
      </main>
    </div>
  );
}
