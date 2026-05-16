import { useState } from "react";
import { Link } from "react-router-dom";
import { registerUser } from "../api/authApi";

const initialForm = {
  full_name: "",
  email: "",
  password: "",
};

export default function Register() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      await registerUser({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
      });
      setSuccessMessage(
        "Account created successfully. Please log in."
      );
      setForm(initialForm);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Registration failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Create your RentalAI account</h1>
        <p className="page-subtitle">Register with your email and password</p>
      </header>

      <section className="card" aria-label="Register form">
        <form className="form-stack" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">Full name</span>
            <input
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              placeholder="e.g. Jane Smith"
              className="input"
              autoComplete="name"
              disabled={loading}
            />
          </label>

          <label className="field">
            <span className="field-label">Email</span>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="user@example.com"
              className="input"
              autoComplete="email"
              required
              disabled={loading}
            />
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Choose a password"
              className="input"
              autoComplete="new-password"
              required
              disabled={loading}
            />
          </label>

          <button type="submit" className="btn" disabled={loading}>
            {loading ? "Registering..." : "Register"}
          </button>

          {successMessage ? (
            <div className="register-success" role="status">
              <p className="text-success">{successMessage}</p>
              <Link to="/login" className="register-login-link">
                Go to Login
              </Link>
            </div>
          ) : null}
          {error ? (
            <p className="text-error" role="alert">
              {error}
            </p>
          ) : null}
        </form>
      </section>
    </div>
  );
}
