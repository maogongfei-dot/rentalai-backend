import { useRef, useState } from "react";
import { mockContractRisks } from "../data/contractMockRisks.js";
import "./ContractCenter.css";

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".pdf", ".doc", ".docx"];

const CONTRACT_MODULES = [
  {
    id: "upload-contract",
    title: "Upload Contract",
    description: "Upload a tenancy agreement for AI-assisted review.",
    active: true,
  },
  {
    id: "risk-detection",
    title: "Risk Detection",
    description:
      "Identify risky clauses, unclear terms, and potential tenant concerns.",
    active: true,
  },
  {
    id: "missing-clauses",
    title: "Missing Clauses",
    description:
      "Check whether important tenancy terms are missing or weak.",
  },
  {
    id: "contract-ai-chat",
    title: "Contract AI Chat",
    description:
      "Ask questions about your tenancy agreement and rental obligations.",
  },
];

function getFileExtension(name) {
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index).toLowerCase() : "";
}

function isAcceptedContractFile(file) {
  const ext = getFileExtension(file.name);
  return ACCEPTED_EXTENSIONS.includes(ext);
}

function UploadContractSection() {
  const inputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState("");

  function handleChooseClick() {
    inputRef.current?.click();
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    setFileError("");

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!isAcceptedContractFile(file)) {
      setSelectedFile(null);
      setFileError("Please choose a PDF, DOC, or DOCX file.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_FILE_BYTES) {
      setSelectedFile(null);
      setFileError("File is too large. Maximum size is 10MB.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }

  function handleClearFile() {
    setSelectedFile(null);
    setFileError("");
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleStartMockReview() {
    if (!selectedFile) return;
    console.log("Start mock contract review:", {
      name: selectedFile.name,
      size: selectedFile.size,
      type: selectedFile.type,
    });
  }

  return (
    <section
      id="upload-contract"
      className="contract-upload"
      aria-labelledby="upload-contract-heading"
    >
      <header className="contract-upload__header">
        <h2 id="upload-contract-heading" className="contract-upload__title">
          Upload Contract
        </h2>
        <p className="contract-upload__subtitle">
          Select a tenancy agreement to prepare for mock AI review (no upload to
          server).
        </p>
      </header>

      <div className="card contract-upload__panel">
        <p className="contract-upload__label">Upload tenancy agreement</p>

        <div
          className={`contract-upload__dropzone${selectedFile ? " contract-upload__dropzone--ready" : ""}`}
        >
          <input
            ref={inputRef}
            id="contract-file-input"
            type="file"
            className="contract-upload__input"
            accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
          />

          {!selectedFile ? (
            <>
              <p className="contract-upload__hint">
                Choose a file to begin mock contract review.
              </p>
              <button
                type="button"
                className="contract-upload__choose-btn"
                onClick={handleChooseClick}
              >
                Choose file
              </button>
            </>
          ) : (
            <>
              <p className="contract-upload__filename" title={selectedFile.name}>
                {selectedFile.name}
              </p>
              <span className="contract-upload__status">Ready for review</span>
              <button
                type="button"
                className="contract-upload__clear-btn"
                onClick={handleClearFile}
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

        <button
          type="button"
          className="contract-upload__review-btn"
          disabled={!selectedFile}
          onClick={handleStartMockReview}
        >
          Start mock review
        </button>
      </div>
    </section>
  );
}

function riskLevelLabel(level) {
  const labels = { low: "Low", medium: "Medium", high: "High" };
  return labels[level] ?? level;
}

function RiskLevelBadge({ level }) {
  return (
    <span className={`contract-risk-badge contract-risk-badge--${level}`}>
      {riskLevelLabel(level)}
    </span>
  );
}

function ContractRiskCard({ risk }) {
  return (
    <li className="card contract-risk-card">
      <div className="contract-risk-card__header">
        <h3 className="contract-risk-card__title">{risk.clause_title}</h3>
        <RiskLevelBadge level={risk.risk_level} />
      </div>
      <p className="contract-risk-card__issue">
        <span className="contract-risk-card__label">Issue</span>
        {risk.issue}
      </p>
      <p className="contract-risk-card__explanation">
        <span className="contract-risk-card__label">Explanation</span>
        {risk.explanation}
      </p>
      <p className="contract-risk-card__action">
        <span className="contract-risk-card__label">Suggested action</span>
        {risk.suggested_action}
      </p>
    </li>
  );
}

function RiskDetectionSection({ risks }) {
  const highCount = risks.filter((r) => r.risk_level === "high").length;
  const mediumCount = risks.filter((r) => r.risk_level === "medium").length;

  return (
    <section
      id="risk-detection"
      className="contract-risks"
      aria-labelledby="risk-detection-heading"
    >
      <header className="contract-risks__header">
        <h2 id="risk-detection-heading" className="contract-risks__title">
          Risk Detection
        </h2>
        <p className="contract-risks__subtitle">
          {risks.length} issue{risks.length === 1 ? "" : "s"} found ·{" "}
          {highCount} high · {mediumCount} medium · mock data
        </p>
      </header>

      <ul className="contract-risks__list">
        {risks.map((risk) => (
          <ContractRiskCard key={risk.id} risk={risk} />
        ))}
      </ul>
    </section>
  );
}

export default function ContractCenter() {
  return (
    <div className="page-shell contract-center">
      <header className="contract-hero">
        <p className="contract-hero__eyebrow">RentalAI Contract Hub</p>
        <h1 className="contract-hero__title">Contract Analysis Center</h1>
        <p className="contract-hero__subtitle">
          Review tenancy agreements, identify rental risks, check missing
          clauses, and understand contract issues.
        </p>
      </header>

      <UploadContractSection />

      <RiskDetectionSection risks={mockContractRisks} />

      <section
        className="contract-modules"
        aria-label="Contract analysis modules"
      >
        <ul className="contract-modules__grid">
          {CONTRACT_MODULES.map((module) => (
            <li key={module.id}>
              <article
                className="card contract-module-card"
                aria-labelledby={`contract-module-${module.id}-title`}
              >
                <h2
                  id={`contract-module-${module.id}-title`}
                  className="contract-module-card__title"
                >
                  {module.title}
                </h2>
                <p className="contract-module-card__text">{module.description}</p>
                {module.active ? (
                  <span className="contract-module-card__badge contract-module-card__badge--live">
                    Live preview
                  </span>
                ) : (
                  <span className="contract-module-card__badge">Coming soon</span>
                )}
              </article>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
