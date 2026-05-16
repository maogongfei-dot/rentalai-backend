import { Link } from "react-router-dom";

export default function Navbar() {
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
      <Link to="/register" className="navbar-link">
        Register
      </Link>
      <Link to="/login" className="navbar-link">
        Login
      </Link>
    </nav>
  );
}
