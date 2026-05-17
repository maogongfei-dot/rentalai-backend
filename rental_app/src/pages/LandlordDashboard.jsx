import { useState } from "react";
import { MOCK_LANDLORD_LISTINGS } from "../data/landlordMockListings.js";
import "./LandlordDashboard.css";

const LANDLORD_MODULES = [
  {
    id: "my-listings",
    title: "My Listings",
    description: "Create, edit, and manage your rental listings.",
    active: true,
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

function formatPricePerNight(amount) {
  return `\u00A3${amount.toLocaleString("en-GB")}`;
}

function formatBedrooms(count) {
  if (count === 0) return "Studio";
  return count === 1 ? "1 bedroom" : `${count} bedrooms`;
}

function formatOccupancy(rate) {
  return `${rate}%`;
}

function listingStatusLabel(status) {
  const labels = {
    active: "Active",
    draft: "Draft",
    paused: "Paused",
  };
  return labels[status] ?? status;
}

function ListingStatusBadge({ status }) {
  return (
    <span
      className={`landlord-listing-status landlord-listing-status--${status}`}
    >
      {listingStatusLabel(status)}
    </span>
  );
}

function ListingCard({ listing, onEdit, onRemove }) {
  return (
    <li className="landlord-listing-card card">
      <div className="landlord-listing-card__header">
        <h3 className="landlord-listing-card__title">{listing.title}</h3>
        <ListingStatusBadge status={listing.listing_status} />
      </div>
      <p className="landlord-listing-card__location">{listing.location}</p>
      <p className="landlord-listing-card__price">
        {formatPricePerNight(listing.price_per_night)}
        <span className="landlord-listing-card__price-unit"> / night</span>
      </p>

      <dl className="landlord-listing-card__stats">
        <div className="landlord-listing-card__stat">
          <dt>Bedrooms</dt>
          <dd>{formatBedrooms(listing.bedrooms)}</dd>
        </div>
        <div className="landlord-listing-card__stat">
          <dt>Occupancy</dt>
          <dd>{formatOccupancy(listing.occupancy_rate)}</dd>
        </div>
        <div className="landlord-listing-card__stat">
          <dt>Views</dt>
          <dd>{listing.views.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-listing-card__stat">
          <dt>Enquiries</dt>
          <dd>{listing.enquiries.toLocaleString("en-GB")}</dd>
        </div>
      </dl>

      <div className="landlord-listing-card__actions">
        <button
          type="button"
          className="landlord-listing-btn landlord-listing-btn--primary"
          onClick={() => onEdit(listing)}
        >
          Edit Listing
        </button>
        <button
          type="button"
          className="landlord-listing-btn landlord-listing-btn--danger"
          onClick={() => onRemove(listing.id)}
        >
          Remove Listing
        </button>
      </div>
    </li>
  );
}

export default function LandlordDashboard() {
  const [listings, setListings] = useState(MOCK_LANDLORD_LISTINGS);

  function handleEditListing(listing) {
    console.log("Edit listing:", listing.id, listing);
  }

  function handleRemoveListing(id) {
    setListings((prev) => prev.filter((item) => item.id !== id));
  }

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
        id="my-listings"
        className="landlord-listings"
        aria-labelledby="my-listings-heading"
      >
        <header className="landlord-listings__header">
          <h2 id="my-listings-heading" className="landlord-listings__title">
            My Listings
          </h2>
          <p className="landlord-listings__subtitle">
            {listings.length === 0
              ? "You have no listings on this page."
              : `${listings.length} listing${listings.length === 1 ? "" : "s"} shown (mock data)`}
          </p>
        </header>

        {listings.length === 0 ? (
          <p className="landlord-listings__empty card">
            All mock listings were removed. Refresh the page to restore them.
          </p>
        ) : (
          <ul className="landlord-listings__grid">
            {listings.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                onEdit={handleEditListing}
                onRemove={handleRemoveListing}
              />
            ))}
          </ul>
        )}
      </section>

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
            {module.active ? (
              <span className="landlord-dashboard-card-badge landlord-dashboard-card-badge--live">
                Live preview
              </span>
            ) : (
              <span className="landlord-dashboard-card-badge">Coming soon</span>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
