import {
  mockAreaScore,
  mockTransportAccess,
  mockLocalAmenities,
  getOverallScoreHint,
  getTransportRatingHint,
  getAmenitiesRatingHint,
} from "../data/areaMockData.js";
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
    status: "Coming soon",
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
      <TransportAccessSection data={mockTransportAccess} />
      <LocalAmenitiesSection data={mockLocalAmenities} />

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
