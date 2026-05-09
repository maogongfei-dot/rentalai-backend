export default function HomePage() {
  return (
    <div className="page-shell">
      <header className="page-header">
        <h1 className="page-title">Welcome to RentalAI</h1>
        <p className="page-subtitle">
          Browse short-term rentals and publish listings in one place.
        </p>
      </header>
      <section className="card" aria-label="Introduction">
        <h2 className="home-card-title">RentalAI Home</h2>
        <p className="home-card-text">
          Use the navigation above to explore short rent recommendations or create
          a new listing.
        </p>
      </section>
    </div>
  );
}
