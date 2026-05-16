import { aiGuides } from "../data/aiGuides.js";
import "./GuideLibrary.css";

function dispatchRentalAIChatMessage(message) {
  window.dispatchEvent(
    new CustomEvent("rentalai-send-chat-message", {
      detail: { message },
    }),
  );
}

export default function GuideLibrary() {
  return (
    <div className="page-shell guide-library">
      <header className="page-header">
        <h1 className="page-title">AI Guide Library</h1>
        <p className="page-subtitle">
          Choose a guide to help you understand properties, contracts, landlord
          tools, and rental risks.
        </p>
      </header>

      <div className="guide-library-grid">
        {aiGuides.map((guide) => (
          <article
            key={guide.id}
            className="card guide-library-card"
            aria-labelledby={`guide-title-${guide.id}`}
          >
            <div className="guide-library-card__head">
              <span className="guide-library-card__category">{guide.category}</span>
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
        ))}
      </div>
    </div>
  );
}
