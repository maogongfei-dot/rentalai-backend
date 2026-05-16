import { useMemo, useState } from "react";
import { aiGuides } from "../data/aiGuides.js";
import "./GuideLibrary.css";

const FILTER_OPTIONS = [
  { id: "all", label: "All" },
  { id: "property", label: "Property" },
  { id: "contract", label: "Contract" },
  { id: "landlord", label: "Landlord" },
];

function dispatchRentalAIChatMessage(message) {
  window.dispatchEvent(
    new CustomEvent("rentalai-send-chat-message", {
      detail: { message },
    }),
  );
}

function guideMatchesQuery(guide, normalizedQuery) {
  if (!normalizedQuery) return true;
  const parts = [
    guide.title,
    guide.category,
    guide.description,
    ...(guide.starter_questions ?? []),
    ...(guide.suggested_actions ?? []),
  ];
  return parts.some(
    (s) => typeof s === "string" && s.toLowerCase().includes(normalizedQuery),
  );
}

export default function GuideLibrary() {
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const categoryScopedGuides = useMemo(() => {
    if (categoryFilter === "all") return aiGuides;
    return aiGuides.filter((g) => g.category === categoryFilter);
  }, [categoryFilter]);

  const visibleGuides = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return categoryScopedGuides;
    return categoryScopedGuides.filter((g) => guideMatchesQuery(g, q));
  }, [categoryScopedGuides, searchQuery]);

  const emptyMessage =
    categoryScopedGuides.length === 0
      ? "No guides match this category."
      : "No guides found. Try another keyword.";

  return (
    <div className="page-shell guide-library">
      <header className="page-header">
        <h1 className="page-title">AI Guide Library</h1>
        <p className="page-subtitle">
          Choose a guide to help you understand properties, contracts, landlord
          tools, and rental risks.
        </p>
      </header>

      <div className="guide-library-search-wrap" role="search">
        <label className="guide-library-search-label" htmlFor="guide-library-search">
          Search guides
        </label>
        <input
          id="guide-library-search"
          type="search"
          className="guide-library-search input"
          placeholder="Search guides, questions, or actions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          autoComplete="off"
        />
      </div>

      <div
        className="guide-library-filters"
        role="toolbar"
        aria-label="Filter guides by category"
      >
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            className={
              categoryFilter === opt.id
                ? "guide-library-filter-btn guide-library-filter-btn--active"
                : "guide-library-filter-btn"
            }
            aria-pressed={categoryFilter === opt.id}
            onClick={() => setCategoryFilter(opt.id)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="guide-library-grid">
        {visibleGuides.length === 0 ? (
          <p className="guide-library-empty">{emptyMessage}</p>
        ) : (
          visibleGuides.map((guide) => (
            <article
              key={guide.id}
              className="card guide-library-card"
              aria-labelledby={`guide-title-${guide.id}`}
            >
              <div className="guide-library-card__head">
                <span className="guide-library-card__category">
                  {guide.category}
                </span>
                <h2
                  id={`guide-title-${guide.id}`}
                  className="guide-library-card__title"
                >
                  {guide.title}
                </h2>
              </div>
              <p className="guide-library-card__desc">{guide.description}</p>

              <div className="guide-library-card__block">
                <h3 className="guide-library-card__label">Starter questions</h3>
                <div
                  className="guide-library-chips"
                  role="group"
                  aria-label={`Starter questions for ${guide.title}`}
                >
                  {(guide.starter_questions ?? []).map((q, qi) => (
                    <button
                      key={`${guide.id}-sq-${qi}`}
                      type="button"
                      className="guide-library-chip"
                      onClick={() => dispatchRentalAIChatMessage(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <div className="guide-library-card__block">
                <h3 className="guide-library-card__label">Suggested actions</h3>
                <div
                  className="guide-library-chips"
                  role="group"
                  aria-label={`Suggested actions for ${guide.title}`}
                >
                  {(guide.suggested_actions ?? []).map((a, ai) => (
                    <button
                      key={`${guide.id}-sa-${ai}`}
                      type="button"
                      className="guide-library-chip guide-library-chip--action"
                      onClick={() => dispatchRentalAIChatMessage(a)}
                    >
                      {a}
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
