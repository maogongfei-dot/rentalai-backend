import { useState } from "react";
import { MOCK_LANDLORD_BOOKING_REQUESTS } from "../data/landlordMockBookingRequests.js";
import { MOCK_LANDLORD_LISTINGS } from "../data/landlordMockListings.js";
import { MOCK_AI_LISTING_ASSISTANT_FEATURES } from "../data/landlordMockAiAssistant.js";
import { MOCK_LANDLORD_PROPERTY_PERFORMANCE } from "../data/landlordMockPropertyPerformance.js";
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
    active: true,
  },
  {
    id: "property-performance",
    title: "Property Performance",
    description: "Track views, enquiries, occupancy, and listing quality.",
    active: true,
  },
  {
    id: "ai-listing-assistant",
    title: "AI Listing Assistant",
    description:
      "Improve descriptions, pricing, photos, and rental appeal with AI guidance.",
    active: true,
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

function formatStayDate(isoDate) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function bookingStatusLabel(status) {
  const labels = {
    pending: "Pending",
    accepted: "Accepted",
    declined: "Declined",
  };
  return labels[status] ?? status;
}

function BookingStatusBadge({ status }) {
  return (
    <span
      className={`landlord-booking-status landlord-booking-status--${status}`}
    >
      {bookingStatusLabel(status)}
    </span>
  );
}

function BookingRequestCard({ request, onAccept, onDecline }) {
  const isResolved =
    request.status === "accepted" || request.status === "declined";

  return (
    <li className="landlord-booking-card card">
      <div className="landlord-booking-card__header">
        <h3 className="landlord-booking-card__guest">{request.guest_name}</h3>
        <BookingStatusBadge status={request.status} />
      </div>
      <p className="landlord-booking-card__property">{request.property_title}</p>

      <dl className="landlord-booking-card__details">
        <div className="landlord-booking-card__detail">
          <dt>Check-in</dt>
          <dd>{formatStayDate(request.check_in)}</dd>
        </div>
        <div className="landlord-booking-card__detail">
          <dt>Check-out</dt>
          <dd>{formatStayDate(request.check_out)}</dd>
        </div>
        <div className="landlord-booking-card__detail">
          <dt>Guests</dt>
          <dd>
            {request.guests} guest{request.guests === 1 ? "" : "s"}
          </dd>
        </div>
      </dl>

      <blockquote className="landlord-booking-card__message">
        <p>{request.message}</p>
      </blockquote>

      <div className="landlord-booking-card__actions">
        <button
          type="button"
          className="landlord-booking-btn landlord-booking-btn--accept"
          disabled={isResolved}
          onClick={() => onAccept(request.id)}
        >
          Accept
        </button>
        <button
          type="button"
          className="landlord-booking-btn landlord-booking-btn--decline"
          disabled={isResolved}
          onClick={() => onDecline(request.id)}
        >
          Decline
        </button>
      </div>
    </li>
  );
}

function formatPercent(value) {
  return `${value}%`;
}

function formatRating(value) {
  return value.toFixed(1);
}

function formatPerformanceScore(value) {
  return `${value}/100`;
}

function getTopPerformingListing(performanceData) {
  if (performanceData.length === 0) return null;
  return performanceData.reduce((best, item) =>
    item.performance_score > best.performance_score ? item : best,
  );
}

function PerformanceScoreBadge({ score, isTop }) {
  return (
    <span
      className={`landlord-performance-score${isTop ? " landlord-performance-score--top" : ""}`}
      aria-label={`Performance score ${score} out of 100`}
    >
      {formatPerformanceScore(score)}
    </span>
  );
}

function PropertyPerformanceCard({ item, isTop }) {
  return (
    <li
      className={`landlord-performance-card card${isTop ? " landlord-performance-card--top" : ""}`}
    >
      <div className="landlord-performance-card__header">
        <h3 className="landlord-performance-card__title">{item.property_title}</h3>
        <PerformanceScoreBadge score={item.performance_score} isTop={isTop} />
      </div>

      <dl className="landlord-performance-card__metrics">
        <div className="landlord-performance-card__metric">
          <dt>Total views</dt>
          <dd>{item.total_views.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-performance-card__metric">
          <dt>Total enquiries</dt>
          <dd>{item.total_enquiries.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-performance-card__metric">
          <dt>Occupancy</dt>
          <dd>{formatPercent(item.occupancy_rate)}</dd>
        </div>
        <div className="landlord-performance-card__metric">
          <dt>Avg. rating</dt>
          <dd>{formatRating(item.average_rating)}</dd>
        </div>
        <div className="landlord-performance-card__metric">
          <dt>Response rate</dt>
          <dd>{formatPercent(item.response_rate)}</dd>
        </div>
        <div className="landlord-performance-card__metric landlord-performance-card__metric--highlight">
          <dt>Performance score</dt>
          <dd>{formatPerformanceScore(item.performance_score)}</dd>
        </div>
      </dl>
    </li>
  );
}

function AiAssistantFeatureCard({ feature, onTry }) {
  return (
    <li className="landlord-ai-card card">
      <h3 className="landlord-ai-card__title">{feature.title}</h3>
      <p className="landlord-ai-card__description">{feature.description}</p>
      <button
        type="button"
        className="landlord-ai-card__btn"
        onClick={() => onTry(feature)}
      >
        Try this
      </button>
    </li>
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
  const [bookingRequests, setBookingRequests] = useState(
    MOCK_LANDLORD_BOOKING_REQUESTS,
  );

  function handleEditListing(listing) {
    console.log("Edit listing:", listing.id, listing);
  }

  function handleRemoveListing(id) {
    setListings((prev) => prev.filter((item) => item.id !== id));
  }

  function handleAcceptRequest(id) {
    setBookingRequests((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: "accepted" } : item,
      ),
    );
  }

  function handleDeclineRequest(id) {
    setBookingRequests((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, status: "declined" } : item,
      ),
    );
  }

  function handleTryAiFeature(feature) {
    console.log("AI Listing Assistant:", feature.id, feature.title);
  }

  const pendingRequestCount = bookingRequests.filter(
    (r) => r.status === "pending",
  ).length;

  const propertyPerformance = MOCK_LANDLORD_PROPERTY_PERFORMANCE;
  const topPerforming = getTopPerformingListing(propertyPerformance);

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
        id="booking-requests"
        className="landlord-bookings"
        aria-labelledby="booking-requests-heading"
      >
        <header className="landlord-bookings__header">
          <h2
            id="booking-requests-heading"
            className="landlord-bookings__title"
          >
            Booking Requests
          </h2>
          <p className="landlord-bookings__subtitle">
            {bookingRequests.length === 0
              ? "No booking requests on this page."
              : `${pendingRequestCount} pending · ${bookingRequests.length} total (mock data)`}
          </p>
        </header>

        {bookingRequests.length === 0 ? (
          <p className="landlord-bookings__empty card">
            No booking requests to show.
          </p>
        ) : (
          <ul className="landlord-bookings__list">
            {bookingRequests.map((request) => (
              <BookingRequestCard
                key={request.id}
                request={request}
                onAccept={handleAcceptRequest}
                onDecline={handleDeclineRequest}
              />
            ))}
          </ul>
        )}
      </section>

      <section
        id="property-performance"
        className="landlord-performance"
        aria-labelledby="property-performance-heading"
      >
        <header className="landlord-performance__header">
          <h2
            id="property-performance-heading"
            className="landlord-performance__title"
          >
            Property Performance
          </h2>
          <p className="landlord-performance__subtitle">
            {propertyPerformance.length} propert
            {propertyPerformance.length === 1 ? "y" : "ies"} tracked (mock data)
          </p>
        </header>

        {topPerforming ? (
          <p className="landlord-performance__summary card" role="status">
            Top performing listing:{" "}
            <strong>{topPerforming.property_title}</strong>
          </p>
        ) : null}

        {propertyPerformance.length === 0 ? (
          <p className="landlord-performance__empty card">
            No performance data to show.
          </p>
        ) : (
          <ul className="landlord-performance__grid">
            {propertyPerformance.map((item) => (
              <PropertyPerformanceCard
                key={item.id}
                item={item}
                isTop={topPerforming?.id === item.id}
              />
            ))}
          </ul>
        )}
      </section>

      <section
        id="ai-listing-assistant"
        className="landlord-ai"
        aria-labelledby="ai-listing-assistant-heading"
      >
        <header className="landlord-ai__header">
          <h2
            id="ai-listing-assistant-heading"
            className="landlord-ai__title"
          >
            AI Listing Assistant
          </h2>
          <p className="landlord-ai__subtitle">
            Mock tools to help optimise your listings — no real AI connected yet.
          </p>
        </header>

        <ul className="landlord-ai__grid">
          {MOCK_AI_LISTING_ASSISTANT_FEATURES.map((feature) => (
            <AiAssistantFeatureCard
              key={feature.id}
              feature={feature}
              onTry={handleTryAiFeature}
            />
          ))}
        </ul>
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
