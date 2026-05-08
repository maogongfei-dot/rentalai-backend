import { useState } from "react";

const initialForm = {
  title: "",
  location: "",
  postcode: "",
  price_per_day: "",
  available_dates: "",
  min_days: "",
  max_days: "",
  landlord_id: "",
  description: "",
};

export default function CreateShortRentPage() {
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function buildPayload() {
    const dates = form.available_dates
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const now = new Date();
    const isoDate = now.toISOString().slice(0, 10);

    // id / created_at are not part of the visible form (per spec), but the
    // backend primary key requires them; auto-generate on submit.
    const idSuffix = Math.random().toString(36).slice(2, 10);
    const generatedId = `short-rent-${now.getTime()}-${idSuffix}`;

    return {
      id: generatedId,
      title: form.title,
      location: form.location,
      postcode: form.postcode,
      price_per_day: form.price_per_day === "" ? null : Number(form.price_per_day),
      available_dates: dates,
      min_days: form.min_days === "" ? null : Number(form.min_days),
      max_days: form.max_days === "" ? null : Number(form.max_days),
      landlord_id: form.landlord_id,
      description: form.description,
      created_at: isoDate,
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setSuccessMessage("");
    setError("");

    try {
      const apiResponse = await fetch(
        "http://localhost:8000/api/short-rent/create",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildPayload()),
        }
      );
      const response = await apiResponse.json();

      if (response.success === true) {
        setSuccessMessage("Short rent listing created successfully.");
        setForm(initialForm);
      } else {
        setError(response.error || "Failed to create short rent listing");
      }
    } catch (e) {
      setError("Failed to create short rent listing");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Create Short Rent Listing</h1>
        <p style={styles.subtitle}>Publish a short-term rental on RentalAI</p>
      </header>

      <section style={styles.card} aria-label="Create short-term rental">
        <form style={styles.form} onSubmit={handleSubmit}>
          <label style={styles.label}>
            <span style={styles.labelText}>Title</span>
            <input
              type="text"
              name="title"
              value={form.title}
              onChange={handleChange}
              placeholder="e.g. Bright double room near Camden"
              style={styles.input}
              required
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Location</span>
            <input
              type="text"
              name="location"
              value={form.location}
              onChange={handleChange}
              placeholder="e.g. London"
              style={styles.input}
              required
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Postcode</span>
            <input
              type="text"
              name="postcode"
              value={form.postcode}
              onChange={handleChange}
              placeholder="e.g. E1 6AN"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Price per day</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="price_per_day"
              value={form.price_per_day}
              onChange={handleChange}
              placeholder="e.g. 55"
              style={styles.input}
              required
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Available dates</span>
            <input
              type="text"
              name="available_dates"
              value={form.available_dates}
              onChange={handleChange}
              placeholder="Comma-separated, e.g. 2026-06-01, 2026-06-02"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Minimum days</span>
            <input
              type="number"
              min="1"
              step="1"
              name="min_days"
              value={form.min_days}
              onChange={handleChange}
              placeholder="e.g. 2"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Maximum days</span>
            <input
              type="number"
              min="1"
              step="1"
              name="max_days"
              value={form.max_days}
              onChange={handleChange}
              placeholder="e.g. 14"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Landlord ID</span>
            <input
              type="text"
              name="landlord_id"
              value={form.landlord_id}
              onChange={handleChange}
              placeholder="e.g. landlord-001"
              style={styles.input}
            />
          </label>

          <label style={styles.label}>
            <span style={styles.labelText}>Description</span>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="Short description of the property"
              rows={4}
              style={{ ...styles.input, resize: "vertical" }}
            />
          </label>

          <button type="submit" style={styles.button} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit"}
          </button>

          {successMessage ? (
            <p style={styles.successText}>{successMessage}</p>
          ) : null}
          {error ? <p style={styles.errorText}>{error}</p> : null}
        </form>
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
    background: "#fff",
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
    fontFamily: "inherit",
  },
  button: {
    marginTop: "0.5rem",
    padding: "0.65rem 1rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#fff",
    background: "#2563eb",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
  },
  successText: {
    margin: 0,
    fontSize: "0.95rem",
    color: "#15803d",
  },
  errorText: {
    margin: 0,
    fontSize: "0.95rem",
    color: "#b91c1c",
  },
};
