import { useState } from "react";
import { fetchShortRentRecommendations } from "../api/shortRentApi";

export default function ShortRentPage() {
  const [filters, setFilters] = useState({
    location: "",
    min_price: "",
    max_price: "",
  });

  const mockResults = [
    {
      id: "mock-1",
      title: "Bright double room near Camden",
      source: "RentalAI",
      source_type: "internal",
      location: "London",
      price_per_day: 42,
      explanation:
        "这是平台内短租房源，信息来自房东发布，适合优先查看。每日价格较低，性价比较高。",
    },
    {
      id: "mock-2",
      title: "Studio flat Northern Quarter",
      source: "OpenRent",
      source_type: "external",
      location: "Manchester",
      price_per_day: 38,
      explanation:
        "这是外部平台短租房源，适合作为补充比较，需要跳转原平台查看详情。每日价格较低，性价比较高。",
    },
    {
      id: "mock-3",
      title: "Waterfront 2-bed short let",
      source: "SpareRoom",
      source_type: "external",
      location: "Liverpool",
      price_per_day: 72,
      explanation:
        "这是外部平台短租房源，适合作为补充比较，需要跳转原平台查看详情。",
    },
  ];
  const [results, setResults] = useState(mockResults);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleInputChange(event) {
    const { name, value } = event.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  async function handleSearch(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    console.log("Short rent search filters:", filters);

    try {
      const response = await fetchShortRentRecommendations();

      if (response.success === true) {
        setResults(response.data);
      } else {
        setError(response.error || "Failed to load short rent results");
      }
    } catch (e) {
      setError("Failed to load short rent results");
    } finally {
      setLoading(false);
    }
  }

  function formatSourceLine(item) {
    if (item.source_type === "internal") {
      return "RentalAI";
    }
    if (item.source_type === "external") {
      return item.source ? `External Platform (${item.source})` : "External Platform";
    }
    return item.source || "";
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Short Rent Finder</h1>
        <p className="page-subtitle">
          Find short-term rentals from RentalAI and external platforms
        </p>
      </header>

      <section className="card" aria-label="Search short-term rentals">
        <form className="form-stack" onSubmit={handleSearch}>
          <label className="field">
            <span className="field-label">Location</span>
            <input
              type="text"
              name="location"
              value={filters.location}
              onChange={handleInputChange}
              placeholder="e.g. London, Manchester"
              className="input"
            />
          </label>
          <label className="field">
            <span className="field-label">Min price (per day)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="min_price"
              value={filters.min_price}
              onChange={handleInputChange}
              placeholder="0"
              className="input"
            />
          </label>
          <label className="field">
            <span className="field-label">Max price (per day)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="max_price"
              value={filters.max_price}
              onChange={handleInputChange}
              placeholder="e.g. 100"
              className="input"
            />
          </label>
          <button type="submit" className="btn">
            Search
          </button>
        </form>
      </section>

      <section className="section-stack" aria-label="Short rent results">
        <h2 className="section-title">Results</h2>
        {loading ? (
          <p className="feedback-block text-muted">Loading short rent results...</p>
        ) : null}
        {error ? (
          <p className="feedback-block text-error">{error}</p>
        ) : null}
        <ul className="result-list">
          {results.map((item) => (
            <li key={item.id} className="result-card">
              <h3 className="result-card-title">{item.title}</h3>
              <p className="result-row">
                <span className="result-row-label">Source</span>
                {formatSourceLine(item)}
              </p>
              <p className="result-row">
                <span className="result-row-label">Location</span>
                {item.location}
              </p>
              <p className="result-price">
                £{Number(item.price_per_day).toFixed(0)}/day
              </p>
              <p className="result-explanation">{item.explanation}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
