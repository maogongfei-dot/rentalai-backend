import { useState } from "react";
import { createShortRentListing } from "../api/shortRentApi";

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
      const formData = buildPayload();
      const response = await createShortRentListing(formData);

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
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Create Short Rent Listing</h1>
        <p className="page-subtitle">Publish a short-term rental on RentalAI</p>
      </header>

      <section className="card" aria-label="Create short-term rental">
        <form className="form-stack" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">Title</span>
            <input
              type="text"
              name="title"
              value={form.title}
              onChange={handleChange}
              placeholder="e.g. Bright double room near Camden"
              className="input"
              required
            />
          </label>

          <label className="field">
            <span className="field-label">Location</span>
            <input
              type="text"
              name="location"
              value={form.location}
              onChange={handleChange}
              placeholder="e.g. London"
              className="input"
              required
            />
          </label>

          <label className="field">
            <span className="field-label">Postcode</span>
            <input
              type="text"
              name="postcode"
              value={form.postcode}
              onChange={handleChange}
              placeholder="e.g. E1 6AN"
              className="input"
            />
          </label>

          <label className="field">
            <span className="field-label">Price per day</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="price_per_day"
              value={form.price_per_day}
              onChange={handleChange}
              placeholder="e.g. 55"
              className="input"
              required
            />
          </label>

          <label className="field">
            <span className="field-label">Available dates</span>
            <input
              type="text"
              name="available_dates"
              value={form.available_dates}
              onChange={handleChange}
              placeholder="Comma-separated, e.g. 2026-06-01, 2026-06-02"
              className="input"
            />
          </label>

          <label className="field">
            <span className="field-label">Minimum days</span>
            <input
              type="number"
              min="1"
              step="1"
              name="min_days"
              value={form.min_days}
              onChange={handleChange}
              placeholder="e.g. 2"
              className="input"
            />
          </label>

          <label className="field">
            <span className="field-label">Maximum days</span>
            <input
              type="number"
              min="1"
              step="1"
              name="max_days"
              value={form.max_days}
              onChange={handleChange}
              placeholder="e.g. 14"
              className="input"
            />
          </label>

          <label className="field">
            <span className="field-label">Landlord ID</span>
            <input
              type="text"
              name="landlord_id"
              value={form.landlord_id}
              onChange={handleChange}
              placeholder="e.g. landlord-001"
              className="input"
            />
          </label>

          <label className="field">
            <span className="field-label">Description</span>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="Short description of the property"
              rows={4}
              className="input input--multiline"
            />
          </label>

          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit"}
          </button>

          {successMessage ? (
            <p className="text-success">{successMessage}</p>
          ) : null}
          {error ? <p className="text-error">{error}</p> : null}
        </form>
      </section>
    </div>
  );
}
