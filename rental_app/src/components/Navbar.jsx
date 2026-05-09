import { Link } from "react-router-dom";

const navStyle = {
  display: "flex",
  flexDirection: "row",
  alignItems: "center",
  gap: "1.25rem",
  padding: "0.75rem 1.25rem",
  backgroundColor: "#fff",
  boxShadow: "0 1px 3px rgba(0, 0, 0, 0.12)",
};

const linkStyle = {
  color: "#222",
  textDecoration: "none",
};

export default function Navbar() {
  return (
    <nav style={navStyle} aria-label="Main">
      <Link to="/" style={linkStyle}>
        Home
      </Link>
      <Link to="/short-rent" style={linkStyle}>
        Short Rent
      </Link>
      <Link to="/create-short-rent" style={linkStyle}>
        Create Listing
      </Link>
    </nav>
  );
}
