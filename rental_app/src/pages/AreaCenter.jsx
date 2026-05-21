import { mockAreaScore, getOverallScoreHint } from "../data/areaMockData.js";
import "./AreaCenter.css";

const AREA_MODULES = [
  {
    id: "area-score",
    step: "01",
    title: "Area Score",
    description:
      "Review overall location quality and rental suitability.",
    icon: "📍",
    status: "Available",
  },
  {
    id: "transport-access",
    step: "02",
    title: "Transport Access",
    description:
      "Check nearby bus stops, commute options, and transport convenience.",
    icon: "🚌",
    status: "Coming soon",
  },
  {
    id: "safety-risk",
    step: "03",
    title: "Safety & Risk",
    description:
      "Understand safety signals and area-level rental risk.",
    icon: "🛡️",
    status: "Coming soon",
  },
  {
    id: "nearby-facilities",
    step: "04",
    title: "Nearby Facilities",
    description:
      "Explore shops, schools, parks, healthcare, and daily essentials.",
    icon: "🏪",
    status: "Coming soon",
  },
];

const SCORE_METRICS = [
  { key: "transport_score", label: "Transport Score" },
  { key: "safety_score", label: "Safety Score" },
  { key: "facilities_score", label: "Facilities Score" },
  { key: "school_score", label: "School Score" },
  { key: "rent_value_score", label: "Rent Value Score" },
];

function scoreTone(value) {
  if (value >= 80) return "high";
  if (value >= 60) return "mid";
  return "low";
}

function AreaModuleCard({ module }) {
  const isAvailable = module.status === "Available";

  return (
    <li>
      <article
        id={module.id}
        className="card area-module-card"
        aria-labelledby={`${module.id}-heading`}
      >
        <header className="area-module-card__header">
          <span className="area-module-card__step" aria-hidden="true">
            {module.step}
          </span>
          <span className="area-module-card__icon" aria-hidden="true">
            {module.icon}
          </span>
        </header>
        <h2 id={`${module.id}-heading`} className="area-module-card__title">
          {module.title}
        </h2>
        <p className="area-module-card__description">{module.description}</p>
        {isAvailable ? (
          <a className="area-module-card__link" href="#area-score-detail">
            View mock score
          </a>
        ) : (
          <p className="area-module-card__status">{module.status}</p>
        )}
      </article>
    </li>
  );
}

function AreaScoreSection({ data }) {
  const hint = getOverallScoreHint(data.overall_score);

  return (
    <section
      id="area-score-detail"
      className="area-score"
      aria-labelledby="area-score-heading"
    >
      <header className="area-score__header">
        <span className="area-score__step" aria-hidden="true">
          01
        </span>
        <div className="area-score__titles">
          <h2 id="area-score-heading" className="area-score__title">
            Area Score
          </h2>
          <p className="area-score__subtitle">
            Mock location quality breakdown for preview — not connected to live
            data.
          </p>
        </div>
      </header>

      <div className="card area-score-panel">
        <div className="area-score-location">
          <div className="area-score-location__item">
            <p className="area-score-location__label">Postcode</p>
            <p className="area-score-location__value">{data.postcode}</p>
          </div>
          <div className="area-score-location__item">
            <p className="area-score-location__label">Area Name</p>
            <p className="area-score-location__value">{data.area_name}</p>
          </div>
        </div>

        <div className="area-score-overall">
          <div className="area-score-overall__main">
            <p className="area-score-overall__label">Overall Score</p>
            <p
              className={`area-score-overall__value area-score-overall__value--${scoreTone(data.overall_score)}`}
              aria-label={`Overall score ${data.overall_score} out of 100`}
            >
              <span className="area-score-overall__number">
                {data.overall_score}
              </span>
              <span className="area-score-overall__max">/ 100</span>
            </p>
          </div>
          <p
            className={`area-score-hint area-score-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <ul className="area-score-metrics" aria-label="Score breakdown">
          {SCORE_METRICS.map((metric) => {
            const value = data[metric.key];
            return (
              <li key={metric.key}>
                <article
                  className={`area-score-metric area-score-metric--${scoreTone(value)}`}
                >
                  <p className="area-score-metric__label">{metric.label}</p>
                  <p className="area-score-metric__value">{value}</p>
                </article>
              </li>
            );
          })}
        </ul>

        <div className="area-score-summary">
          <p className="area-score-summary__label">Summary</p>
          <p className="area-score-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

export default function AreaCenter() {
  return (
    <div className="page-shell area-center">
      <header className="area-hero">
        <div className="area-hero__top">
          <p className="area-hero__eyebrow">RentalAI Location Hub</p>
          <span className="area-hero__pill">Preview</span>
        </div>
        <h1 className="area-hero__title">Area Analysis Center</h1>
        <p className="area-hero__subtitle">
          Understand location quality, transport access, safety, schools, and
          nearby facilities before choosing a rental property.
        </p>
      </header>

      <AreaScoreSection data={mockAreaScore} />

      <section className="area-modules" aria-label="Area analysis modules">
        <p className="area-modules__intro">
          Choose a module below to explore location insights. Detailed analysis
          tools will be added in upcoming releases.
        </p>
        <ul className="area-modules__grid">
          {AREA_MODULES.map((module) => (
            <AreaModuleCard key={module.id} module={module} />
          ))}
        </ul>
      </section>
    </div>
  );
}
