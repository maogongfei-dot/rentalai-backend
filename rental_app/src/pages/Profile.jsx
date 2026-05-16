import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user, logout } = useAuth();

  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">My RentalAI Account</h1>
        <p className="page-subtitle">Your account details</p>
      </header>

      <section className="card" aria-label="Account details">
        <dl className="profile-details">
          <div className="profile-row">
            <dt>Email</dt>
            <dd>{user?.email ?? "—"}</dd>
          </div>
          <div className="profile-row">
            <dt>Full name</dt>
            <dd>{user?.full_name?.trim() ? user.full_name : "—"}</dd>
          </div>
        </dl>

        <button type="button" className="btn" onClick={logout}>
          Logout
        </button>
      </section>
    </div>
  );
}
