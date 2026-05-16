import { useState } from "react";
import { loginUser } from "../api/authApi";

const TOKEN_STORAGE_KEY = "rentalai_token";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      const { access_token } = await loginUser(email, password);
      localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      setSuccessMessage("Login successful.");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Login to RentalAI</h1>
        <p className="page-subtitle">Sign in with your email and password</p>
      </header>

      <section className="card" aria-label="Login form">
        <form className="form-stack" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">Email</span>
            <input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              className="input"
              autoComplete="current-password"
              required
              disabled={loading}
            />
          </label>

          <button type="submit" className="btn" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>

          {successMessage ? (
            <p className="text-success" role="status">
              {successMessage}
            </p>
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
