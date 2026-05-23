import {
  mockAreaScore,
  mockTransportAccess,
  mockLocalAmenities,
  getOverallScoreHint,
  getTransportRatingHint,
  getAmenitiesRatingHint,
} from "../data/areaMockData.js";
import "./AreaCenter.css";

/**
 * Area Center — mock preview data (frontend only, no API).
 * - mockAreaScore, mockTransportAccess, mockLocalAmenities → areaMockData.js
 * - mockAreaSafety → defined below for Safety & Area Risk
 */
const mockAreaSafety = {
  safety_rating: 72,
  crime_level: "Moderate",
  common_risks: ["Bike theft", "Night-time noise", "Parking issues"],
  suitable_for: ["Students", "Young professionals"],
  caution_notes:
    "Some streets may feel less safe late at night, but daytime access and main-road visibility are generally good.",
  summary:
    "This area has an acceptable safety profile, but renters should pay attention to night-time travel and local street conditions.",
};

const AREA_MODULES = [
  {
    id: "area-score-summary",
    step: "00",
    title: "Area Score Summary",
    description:
      "See combined area, transport, amenities, and safety ratings at a glance.",
    icon: "📊",
    status: "Available",
    linkHref: "#area-score-summary",
    linkLabel: "View summary",
  },
  {
    id: "area-score",
    step: "01",
    title: "Area Score",
    description:
      "Review overall location quality and rental suitability.",
    icon: "📍",
    status: "Available",
    linkHref: "#area-score-detail",
    linkLabel: "View mock score",
  },
  {
    id: "transport-access",
    step: "02",
    title: "Transport Access",
    description:
      "Check nearby bus stops, commute options, and transport convenience.",
    icon: "🚌",
    status: "Available",
    linkHref: "#transport-access-detail",
    linkLabel: "View transport",
  },
  {
    id: "safety-risk",
    step: "03",
    title: "Safety & Risk",
    description:
      "Understand safety signals and area-level rental risk.",
    icon: "🛡️",
    status: "Available",
    linkHref: "#safety-risk-detail",
    linkLabel: "View safety",
  },
  {
    id: "local-amenities",
    step: "04",
    title: "Local Amenities",
    description:
      "Explore shops, schools, parks, healthcare, and daily essentials.",
    icon: "🏪",
    status: "Available",
    linkHref: "#local-amenities-detail",
    linkLabel: "View amenities",
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

const AREA_RATING_KEYS = ["area_rating", "overall_score", "area_score"];
const TRANSPORT_RATING_KEYS = ["transport_rating", "transport_score"];
const AMENITIES_RATING_KEYS = ["amenities_rating", "facilities_rating"];
const SAFETY_RATING_KEYS = ["safety_rating", "safety_score"];

function pickNumericRating(source, keys) {
  if (!source) return null;
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "number" && !Number.isNaN(value)) {
      return value;
    }
  }
  return null;
}

function buildAreaScoreSummary(area, transport, amenities, safety) {
  const area_rating = pickNumericRating(area, AREA_RATING_KEYS);
  const transport_rating = pickNumericRating(transport, TRANSPORT_RATING_KEYS);
  const amenities_rating = pickNumericRating(amenities, AMENITIES_RATING_KEYS);
  const safety_rating = pickNumericRating(safety, SAFETY_RATING_KEYS);

  const ratings = [
    area_rating,
    transport_rating,
    amenities_rating,
    safety_rating,
  ].filter((value) => value != null);

  const overall_area_score = ratings.length
    ? Math.round(
        ratings.reduce((sum, value) => sum + value, 0) / ratings.length,
      )
    : 0;

  return {
    area_rating,
    transport_rating,
    amenities_rating,
    safety_rating,
    overall_area_score,
    summary:
      area?.summary ??
      "Combined area preview scores — detailed module summaries appear below.",
  };
}

function getOverallAreaScoreHint(overallAreaScore) {
  if (overallAreaScore >= 80) {
    return {
      label: "Highly recommended area",
      tone: "highly-recommended",
    };
  }
  if (overallAreaScore >= 60) {
    return {
      label: "Generally suitable area",
      tone: "generally-suitable",
    };
  }
  return {
    label: "Needs careful consideration",
    tone: "needs-consideration",
  };
}

const SUMMARY_RATING_METRICS = [
  { key: "area_rating", label: "Area Rating" },
  { key: "transport_rating", label: "Transport Rating" },
  { key: "amenities_rating", label: "Amenities Rating" },
  { key: "safety_rating", label: "Safety Rating" },
];

function BasicAreaInfoSection({ postcode, areaName }) {
  return (
    <section
      id="basic-area-info"
      className="area-basic"
      aria-labelledby="basic-area-info-heading"
    >
      <header className="area-basic__header">
        <h2 id="basic-area-info-heading" className="area-basic__title">
          Basic Area Info
        </h2>
        <p className="area-basic__subtitle">
          Mock location identifiers for this preview — not connected to live
          address lookup.
        </p>
      </header>

      <div className="area-basic-location">
        <div className="area-basic-location__item">
          <p className="area-basic-location__label">Postcode</p>
          <p className="area-basic-location__value">{postcode}</p>
        </div>
        <div className="area-basic-location__item">
          <p className="area-basic-location__label">Area Name</p>
          <p className="area-basic-location__value">{areaName}</p>
        </div>
      </div>
    </section>
  );
}

function AreaScoreSummarySection({ summary }) {
  const hint = getOverallAreaScoreHint(summary.overall_area_score);

  return (
    <section
      id="area-score-summary"
      className="area-summary"
      aria-labelledby="area-summary-heading"
    >
      <header className="area-summary__header">
        <h2 id="area-summary-heading" className="area-summary__title">
          Area Score Summary
        </h2>
        <p className="area-summary__subtitle">
          Combined preview scores from area, transport, amenities, and safety
          modules — not connected to live data.
        </p>
      </header>

      <div className="card area-summary-panel">
        <div className="area-summary-overall">
          <div className="area-summary-overall__main">
            <p className="area-summary-overall__label">Overall Area Score</p>
            <p
              className={`area-summary-overall__value area-summary-overall__value--${scoreTone(summary.overall_area_score)}`}
              aria-label={`Overall area score ${summary.overall_area_score} out of 100`}
            >
              <span className="area-summary-overall__number">
                {summary.overall_area_score}
              </span>
              <span className="area-summary-overall__max">/ 100</span>
            </p>
          </div>
          <p
            className={`area-summary-hint area-summary-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <ul className="area-summary-metrics" aria-label="Module ratings">
          {SUMMARY_RATING_METRICS.map((metric) => {
            const value = summary[metric.key];
            return (
              <li key={metric.key}>
                <article
                  className={`area-summary-metric area-summary-metric--${scoreTone(value ?? 0)}`}
                >
                  <p className="area-summary-metric__label">{metric.label}</p>
                  <p className="area-summary-metric__value">
                    {value != null ? value : "—"}
                  </p>
                </article>
              </li>
            );
          })}
        </ul>

        <div className="area-summary-text">
          <p className="area-summary-text__label">Summary Text</p>
          <p className="area-summary-text__body">{summary.summary}</p>
        </div>
      </div>
    </section>
  );
}

function getSafetyRatingHint(safetyRating) {
  if (safetyRating >= 80) {
    return {
      label: "Low risk area",
      tone: "low-risk",
    };
  }
  if (safetyRating >= 60) {
    return {
      label: "Moderate risk area",
      tone: "moderate",
    };
  }
  return {
    label: "Higher caution needed",
    tone: "caution",
  };
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
          <a className="area-module-card__link" href={module.linkHref}>
            {module.linkLabel}
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

const TRANSPORT_DETAILS = [
  { key: "nearest_bus_stop", label: "Nearest Bus Stop" },
  { key: "nearest_station", label: "Nearest Station" },
  { key: "walking_time_to_station", label: "Walking Time to Station" },
  {
    key: "estimated_commute_to_city_center",
    label: "Commute to City Centre",
  },
];

function TransportAccessSection({ data }) {
  const hint = getTransportRatingHint(data.transport_rating);

  return (
    <section
      id="transport-access-detail"
      className="area-transport"
      aria-labelledby="transport-access-heading"
    >
      <header className="area-transport__header">
        <span className="area-transport__step" aria-hidden="true">
          02
        </span>
        <div className="area-transport__titles">
          <h2 id="transport-access-heading" className="area-transport__title">
            Transport Access
          </h2>
          <p className="area-transport__subtitle">
            Mock commute and public transport details — not connected to live
            maps or timetables.
          </p>
        </div>
      </header>

      <div className="card area-transport-panel">
        <ul className="area-transport-details" aria-label="Transport details">
          {TRANSPORT_DETAILS.map((item) => (
            <li key={item.key}>
              <article className="area-transport-detail">
                <p className="area-transport-detail__label">{item.label}</p>
                <p className="area-transport-detail__value">{data[item.key]}</p>
              </article>
            </li>
          ))}
        </ul>

        <div className="area-transport-rating">
          <div className="area-transport-rating__main">
            <p className="area-transport-rating__label">Transport Rating</p>
            <p
              className={`area-transport-rating__value area-transport-rating__value--${scoreTone(data.transport_rating)}`}
              aria-label={`Transport rating ${data.transport_rating} out of 100`}
            >
              <span className="area-transport-rating__number">
                {data.transport_rating}
              </span>
              <span className="area-transport-rating__max">/ 100</span>
            </p>
          </div>
          <p
            className={`area-transport-hint area-transport-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <div className="area-transport-night">
          <p className="area-transport-night__label">Night Transport</p>
          <p
            className={`area-transport-night__badge area-transport-night__badge--${data.night_transport_available ? "yes" : "no"}`}
          >
            {data.night_transport_available
              ? "Available"
              : "Not available"}
          </p>
        </div>

        <div className="area-transport-summary">
          <p className="area-transport-summary__label">Summary</p>
          <p className="area-transport-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

function SafetyTagList({ items }) {
  if (!items?.length) {
    return <p className="area-safety-empty">None listed</p>;
  }

  return (
    <ul className="area-safety-list">
      {items.map((item) => (
        <li key={item}>
          <span className="area-safety-list__item">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function SafetyAreaRiskSection({ data }) {
  const hint = getSafetyRatingHint(data.safety_rating);

  return (
    <section
      id="safety-risk-detail"
      className="area-safety"
      aria-labelledby="safety-risk-heading"
    >
      <header className="area-safety__header">
        <span className="area-safety__step" aria-hidden="true">
          03
        </span>
        <div className="area-safety__titles">
          <h2 id="safety-risk-heading" className="area-safety__title">
            Safety & Area Risk
          </h2>
          <p className="area-safety__subtitle">
            Mock safety and risk signals for preview — not connected to live
            crime or incident data.
          </p>
        </div>
      </header>

      <div className="card area-safety-panel">
        <div className="area-safety-rating">
          <div className="area-safety-rating__main">
            <p className="area-safety-rating__label">Safety Rating</p>
            <p
              className={`area-safety-rating__value area-safety-rating__value--${scoreTone(data.safety_rating)}`}
              aria-label={`Safety rating ${data.safety_rating} out of 100`}
            >
              <span className="area-safety-rating__number">
                {data.safety_rating}
              </span>
              <span className="area-safety-rating__max">/ 100</span>
            </p>
          </div>
          <p
            className={`area-safety-hint area-safety-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <div className="area-safety-crime">
          <p className="area-safety-crime__label">Crime Level</p>
          <p className="area-safety-crime__value">{data.crime_level}</p>
        </div>

        <ul className="area-safety-categories" aria-label="Safety details">
          <li>
            <article className="area-safety-category">
              <h3 className="area-safety-category__title">Common Risks</h3>
              <SafetyTagList items={data.common_risks} />
            </article>
          </li>
          <li>
            <article className="area-safety-category">
              <h3 className="area-safety-category__title">Suitable For</h3>
              <SafetyTagList items={data.suitable_for} />
            </article>
          </li>
        </ul>

        <div className="area-safety-caution">
          <p className="area-safety-caution__label">Caution Notes</p>
          <p className="area-safety-caution__text">{data.caution_notes}</p>
        </div>

        <div className="area-safety-summary">
          <p className="area-safety-summary__label">Summary</p>
          <p className="area-safety-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

const AMENITY_CATEGORIES = [
  { key: "supermarkets", label: "Supermarkets" },
  { key: "schools", label: "Schools" },
  { key: "hospitals", label: "Hospitals" },
  { key: "parks", label: "Parks" },
  { key: "gyms", label: "Gyms" },
];

function AmenityList({ items }) {
  if (!items?.length) {
    return <p className="area-amenities-empty">None listed</p>;
  }

  return (
    <ul className="area-amenities-list">
      {items.map((name) => (
        <li key={name}>
          <span className="area-amenities-list__item">{name}</span>
        </li>
      ))}
    </ul>
  );
}

function LocalAmenitiesSection({ data }) {
  const hint = getAmenitiesRatingHint(data.amenities_rating);

  return (
    <section
      id="local-amenities-detail"
      className="area-amenities"
      aria-labelledby="local-amenities-heading"
    >
      <header className="area-amenities__header">
        <span className="area-amenities__step" aria-hidden="true">
          04
        </span>
        <div className="area-amenities__titles">
          <h2 id="local-amenities-heading" className="area-amenities__title">
            Local Amenities
          </h2>
          <p className="area-amenities__subtitle">
            Mock nearby facilities for daily living — not connected to live
            place data.
          </p>
        </div>
      </header>

      <div className="card area-amenities-panel">
        <ul className="area-amenities-categories" aria-label="Local amenities">
          {AMENITY_CATEGORIES.map((category) => (
            <li key={category.key}>
              <article className="area-amenities-category">
                <h3 className="area-amenities-category__title">
                  {category.label}
                </h3>
                <AmenityList items={data[category.key]} />
              </article>
            </li>
          ))}
        </ul>

        <div className="area-amenities-rating">
          <div className="area-amenities-rating__main">
            <p className="area-amenities-rating__label">Amenities Rating</p>
            <p
              className={`area-amenities-rating__value area-amenities-rating__value--${scoreTone(data.amenities_rating)}`}
              aria-label={`Amenities rating ${data.amenities_rating} out of 100`}
            >
              <span className="area-amenities-rating__number">
                {data.amenities_rating}
              </span>
              <span className="area-amenities-rating__max">/ 100</span>
            </p>
          </div>
          <p
            className={`area-amenities-hint area-amenities-hint--${hint.tone}`}
            role="status"
          >
            {hint.label}
          </p>
        </div>

        <div className="area-amenities-summary">
          <p className="area-amenities-summary__label">Summary</p>
          <p className="area-amenities-summary__text">{data.summary}</p>
        </div>
      </div>
    </section>
  );
}

export default function AreaCenter() {
  const areaScoreSummary = buildAreaScoreSummary(
    mockAreaScore,
    mockTransportAccess,
    mockLocalAmenities,
    mockAreaSafety,
  );

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

      <BasicAreaInfoSection
        postcode={mockAreaScore.postcode}
        areaName={mockAreaScore.area_name}
      />
      <AreaScoreSummarySection summary={areaScoreSummary} />
      <TransportAccessSection data={mockTransportAccess} />
      <LocalAmenitiesSection data={mockLocalAmenities} />
      <SafetyAreaRiskSection data={mockAreaSafety} />
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
