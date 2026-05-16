import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, isAuthenticated, loading, logout } = useAuth();

  const displayName =
    (user?.full_name && user.full_name.trim()) || user?.email || "User";

  return (
    <nav className="navbar" aria-label="Main">
      <Link to="/" className="navbar-brand">
        RentalAI
      </Link>
      <Link to="/" className="navbar-link">
        Home
      </Link>
      <Link to="/guides" className="navbar-link">
        AI Guides
      </Link>
      <Link to="/short-rent" className="navbar-link">
        Short Rent
      </Link>
      <Link to="/create-short-rent" className="navbar-link">
        Create Listing
      </Link>

      {!loading && isAuthenticated ? (
        <>
          <Link to="/profile" className="navbar-link">
            Profile
          </Link>
          <span className="navbar-user" title={user?.email}>
            {displayName}
          </span>
          <button
            type="button"
            className="navbar-link navbar-link--button"
            onClick={logout}
          >
            Logout
          </button>
        </>
      ) : null}

      {!loading && !isAuthenticated ? (
        <>
          <Link to="/register" className="navbar-link">
            Register
          </Link>
          <Link to="/login" className="navbar-link">
            Login
          </Link>
        </>
      ) : null}
    </nav>
  );
}
