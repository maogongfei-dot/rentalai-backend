import { useState } from "react";

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

  function handleInputChange(event) {
    const { name, value } = event.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  function handleSearch(event) {
    event.preventDefault();
    console.log("Short rent search filters:", filters);
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
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Short Rent Finder</h1>
        <p style={styles.subtitle}>
          Find short-term rentals from RentalAI and external platforms
        </p>
      </header>

      <section style={styles.card} aria-label="Search short-term rentals">
        <form style={styles.form} onSubmit={handleSearch}>
          <label style={styles.label}>
            <span style={styles.labelText}>Location</span>
            <input
              type="text"
              name="location"
              value={filters.location}
              onChange={handleInputChange}
              placeholder="e.g. London, Manchester"
              style={styles.input}
            />
          </label>
          <label style={styles.label}>
            <span style={styles.labelText}>Min price (per day)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="min_price"
              value={filters.min_price}
              onChange={handleInputChange}
              placeholder="0"
              style={styles.input}
            />
          </label>
          <label style={styles.label}>
            <span style={styles.labelText}>Max price (per day)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="max_price"
              value={filters.max_price}
              onChange={handleInputChange}
              placeholder="e.g. 100"
              style={styles.input}
            />
          </label>
          <button type="submit" style={styles.button}>
            Search
          </button>
        </form>
      </section>

      <section style={styles.resultsSection} aria-label="Short rent results">
        <h2 style={styles.resultsHeading}>Results</h2>
        <ul style={styles.resultList}>
          {mockResults.map((item) => (
            <li key={item.id} style={styles.resultCard}>
              <h3 style={styles.resultTitle}>{item.title}</h3>
              <p style={styles.resultRow}>
                <span style={styles.resultLabel}>Source</span>
                {formatSourceLine(item)}
              </p>
              <p style={styles.resultRow}>
                <span style={styles.resultLabel}>Location</span>
                {item.location}
              </p>
              <p style={styles.resultPrice}>
                £{Number(item.price_per_day).toFixed(0)}/day
              </p>
              <p style={styles.resultExplanation}>{item.explanation}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

const styles = {
  page: {
    maxWidth: 680,
    margin: "0 auto",
    padding: "2rem 1.25rem",
    fontFamily:
      'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    color: "#1a1a1a",
  },
  header: {
    marginBottom: "2rem",
  },
  title: {
    fontSize: "1.75rem",
    fontWeight: 700,
    margin: "0 0 0.5rem",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    margin: 0,
    fontSize: "1rem",
    color: "#555",
    lineHeight: 1.5,
  },
  card: {
    border: "1px solid #e5e5e5",
    borderRadius: 12,
    padding: "1.5rem",
    background: "#fafafa",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "0.35rem",
  },
  labelText: {
    fontSize: "0.875rem",
    fontWeight: 600,
    color: "#333",
  },
  input: {
    padding: "0.6rem 0.75rem",
    fontSize: "1rem",
    border: "1px solid #ccc",
    borderRadius: 8,
    background: "#fff",
  },
  button: {
    marginTop: "0.25rem",
    padding: "0.65rem 1rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#fff",
    background: "#2563eb",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
  },
  resultsSection: {
    marginTop: "2rem",
  },
  resultsHeading: {
    fontSize: "1.125rem",
    fontWeight: 600,
    margin: "0 0 1rem",
    color: "#333",
  },
  resultList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  resultCard: {
    background: "#fff",
    borderRadius: 12,
    padding: "1.25rem 1.35rem",
    margin: 0,
    border: "1px solid #eaeaea",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  resultTitle: {
    margin: "0 0 0.75rem",
    fontSize: "1.05rem",
    fontWeight: 600,
    lineHeight: 1.35,
  },
  resultRow: {
    margin: "0 0 0.4rem",
    fontSize: "0.9rem",
    color: "#444",
    display: "flex",
    flexWrap: "wrap",
    gap: "0.35rem",
    alignItems: "baseline",
  },
  resultLabel: {
    fontWeight: 600,
    color: "#666",
    marginRight: "0.35rem",
  },
  resultPrice: {
    margin: "0.65rem 0 0.5rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#1d4ed8",
  },
  resultExplanation: {
    margin: 0,
    fontSize: "0.875rem",
    color: "#555",
    lineHeight: 1.55,
  },
};
