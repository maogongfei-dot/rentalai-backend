import "./LandlordDashboard.css";

const LANDLORD_MODULES = [
  {
    id: "my-listings",
    title: "My Listings",
    description: "Create, edit, and manage your rental listings.",
  },
  {
    id: "booking-requests",
    title: "Booking Requests",
    description: "Review incoming tenant requests and booking enquiries.",
  },
  {
    id: "property-performance",
    title: "Property Performance",
    description: "Track views, enquiries, occupancy, and listing quality.",
  },
  {
    id: "ai-listing-assistant",
    title: "AI Listing Assistant",
    description:
      "Improve descriptions, pricing, photos, and rental appeal with AI guidance.",
  },
];

export default function LandlordDashboard() {
  return (
    <div className="page-shell landlord-dashboard">
      <header className="landlord-hero">
        <p className="landlord-hero__eyebrow">RentalAI Landlord Hub</p>
        <h1 className="landlord-hero__title">Landlord Center</h1>
        <p className="landlord-hero__subtitle">
          Manage your listings, booking requests, short-rent operations, and
          property performance.
        </p>
      </header>

      <section
        className="landlord-dashboard-grid"
        aria-label="Landlord center modules"
      >
        {LANDLORD_MODULES.map((module) => (
          <article
            key={module.id}
            className="card landlord-dashboard-card"
            aria-labelledby={`landlord-module-${module.id}-title`}
          >
            <h2
              id={`landlord-module-${module.id}-title`}
              className="landlord-dashboard-card-title"
            >
              {module.title}
            </h2>
            <p className="landlord-dashboard-card-text">{module.description}</p>
            <span className="landlord-dashboard-card-badge">Coming soon</span>
          </article>
        ))}
      </section>
    </div>
  );
}
