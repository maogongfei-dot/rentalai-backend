import { useState } from "react";
import {
  mockBookingRequests,
  mockListingAssistantTools,
  mockListings,
  mockPropertyPerformance,
} from "../data/landlordMockData.js";
import "./LandlordDashboard.css";

const QUICK_NAV = [
  { id: "my-listings", label: "Listings" },
  { id: "booking-requests", label: "Requests" },
  { id: "property-performance", label: "Performance" },
  { id: "ai-listing-assistant", label: "AI Assistant" },
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

function formatStayDate(isoDate) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
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

function listingStatusLabel(status) {
  const labels = { active: "Active", draft: "Draft", paused: "Paused" };
  return labels[status] ?? status;
}

function bookingStatusLabel(status) {
  const labels = { pending: "Pending", accepted: "Accepted", declined: "Declined" };
  return labels[status] ?? status;
}

function getTopPerformingListing(performanceData) {
  if (performanceData.length === 0) return null;
  return performanceData.reduce((best, item) =>
    item.performance_score > best.performance_score ? item : best,
  );
}

function computeDashboardSummary(listings, bookingRequests, propertyPerformance) {
  const pendingRequests = bookingRequests.filter(
    (r) => r.status === "pending",
  ).length;
  const averageOccupancy =
    listings.length > 0
      ? Math.round(
          listings.reduce((sum, item) => sum + item.occupancy_rate, 0) /
            listings.length,
        )
      : 0;
  const bestPerformanceScore =
    propertyPerformance.length > 0
      ? Math.max(...propertyPerformance.map((item) => item.performance_score))
      : 0;

  return {
    totalListings: listings.length,
    pendingRequests,
    averageOccupancy,
    bestPerformanceScore,
  };
}

function LandlordBadge({ label, variant }) {
  return (
    <span className={`landlord-badge landlord-badge--${variant}`}>{label}</span>
  );
}

function LandlordSectionHeader({ id, title, subtitle }) {
  return (
    <header className="landlord-section__header">
      <h2 id={`${id}-heading`} className="landlord-section__title">
        {title}
      </h2>
      {subtitle ? (
        <p className="landlord-section__subtitle">{subtitle}</p>
      ) : null}
    </header>
  );
}

function LandlordSummary({ stats }) {
  const items = [
    { label: "Total Listings", value: String(stats.totalListings) },
    { label: "Pending Requests", value: String(stats.pendingRequests) },
    {
      label: "Average Occupancy",
      value: formatOccupancy(stats.averageOccupancy),
    },
    {
      label: "Best Performance Score",
      value: formatPerformanceScore(stats.bestPerformanceScore),
    },
  ];

  return (
    <section className="landlord-summary" aria-label="Dashboard summary">
      <ul className="landlord-summary__grid">
        {items.map((item) => (
          <li key={item.label} className="landlord-summary__card card">
            <span className="landlord-summary__label">{item.label}</span>
            <span className="landlord-summary__value">{item.value}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function LandlordQuickNav() {
  return (
    <nav className="landlord-quick-nav" aria-label="Jump to section">
      <ul className="landlord-quick-nav__list">
        {QUICK_NAV.map((item) => (
          <li key={item.id}>
            <a className="landlord-quick-nav__link" href={`#${item.id}`}>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function BookingRequestCard({ request, onAccept, onDecline }) {
  const isResolved =
    request.status === "accepted" || request.status === "declined";

  return (
    <li className="landlord-panel-card card">
      <div className="landlord-panel-card__header">
        <h3 className="landlord-panel-card__title">{request.guest_name}</h3>
        <LandlordBadge
          label={bookingStatusLabel(request.status)}
          variant={request.status}
        />
      </div>
      <p className="landlord-panel-card__meta">{request.property_title}</p>

      <dl className="landlord-metric-grid">
        <div className="landlord-metric">
          <dt>Check-in</dt>
          <dd>{formatStayDate(request.check_in)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Check-out</dt>
          <dd>{formatStayDate(request.check_out)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Guests</dt>
          <dd>
            {request.guests} guest{request.guests === 1 ? "" : "s"}
          </dd>
        </div>
      </dl>

      <blockquote className="landlord-panel-card__quote">
        <p>{request.message}</p>
      </blockquote>

      <div className="landlord-panel-card__actions">
        <button
          type="button"
          className="landlord-btn landlord-btn--success"
          disabled={isResolved}
          onClick={() => onAccept(request.id)}
        >
          Accept
        </button>
        <button
          type="button"
          className="landlord-btn landlord-btn--danger"
          disabled={isResolved}
          onClick={() => onDecline(request.id)}
        >
          Decline
        </button>
      </div>
    </li>
  );
}

function PropertyPerformanceCard({ item, isTop }) {
  return (
    <li
      className={`landlord-panel-card card${isTop ? " landlord-panel-card--highlight" : ""}`}
    >
      <div className="landlord-panel-card__header">
        <h3 className="landlord-panel-card__title">{item.property_title}</h3>
        <span
          className={`landlord-score-pill${isTop ? " landlord-score-pill--top" : ""}`}
          aria-label={`Performance score ${item.performance_score} out of 100`}
        >
          {formatPerformanceScore(item.performance_score)}
        </span>
      </div>

      <dl className="landlord-metric-grid landlord-metric-grid--triple">
        <div className="landlord-metric">
          <dt>Total views</dt>
          <dd>{item.total_views.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Total enquiries</dt>
          <dd>{item.total_enquiries.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Occupancy</dt>
          <dd>{formatPercent(item.occupancy_rate)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Avg. rating</dt>
          <dd>{formatRating(item.average_rating)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Response rate</dt>
          <dd>{formatPercent(item.response_rate)}</dd>
        </div>
        <div className="landlord-metric landlord-metric--emphasis">
          <dt>Performance score</dt>
          <dd>{formatPerformanceScore(item.performance_score)}</dd>
        </div>
      </dl>
    </li>
  );
}

function AiAssistantFeatureCard({ feature, onTry }) {
  return (
    <li className="landlord-panel-card card landlord-panel-card--stack">
      <h3 className="landlord-panel-card__title">{feature.title}</h3>
      <p className="landlord-panel-card__desc">{feature.description}</p>
      <button
        type="button"
        className="landlord-btn landlord-btn--primary"
        onClick={() => onTry(feature)}
      >
        Try this
      </button>
    </li>
  );
}

function ListingCard({ listing, onEdit, onRemove }) {
  return (
    <li className="landlord-panel-card card">
      <div className="landlord-panel-card__header">
        <h3 className="landlord-panel-card__title">{listing.title}</h3>
        <LandlordBadge
          label={listingStatusLabel(listing.listing_status)}
          variant={listing.listing_status}
        />
      </div>
      <p className="landlord-panel-card__meta">{listing.location}</p>
      <p className="landlord-panel-card__price">
        {formatPricePerNight(listing.price_per_night)}
        <span className="landlord-panel-card__price-unit"> / night</span>
      </p>

      <dl className="landlord-metric-grid">
        <div className="landlord-metric">
          <dt>Bedrooms</dt>
          <dd>{formatBedrooms(listing.bedrooms)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Occupancy</dt>
          <dd>{formatOccupancy(listing.occupancy_rate)}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Views</dt>
          <dd>{listing.views.toLocaleString("en-GB")}</dd>
        </div>
        <div className="landlord-metric">
          <dt>Enquiries</dt>
          <dd>{listing.enquiries.toLocaleString("en-GB")}</dd>
        </div>
      </dl>

      <div className="landlord-panel-card__actions">
        <button
          type="button"
          className="landlord-btn landlord-btn--primary"
          onClick={() => onEdit(listing)}
        >
          Edit Listing
        </button>
        <button
          type="button"
          className="landlord-btn landlord-btn--danger"
          onClick={() => onRemove(listing.id)}
        >
          Remove Listing
        </button>
      </div>
    </li>
  );
}

export default function LandlordDashboard() {
  const [listings, setListings] = useState(mockListings);
  const [bookingRequests, setBookingRequests] = useState(mockBookingRequests);

  const propertyPerformance = mockPropertyPerformance;
  const topPerforming = getTopPerformingListing(propertyPerformance);
  const summary = computeDashboardSummary(
    listings,
    bookingRequests,
    propertyPerformance,
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

  return (
    <div className="page-shell landlord-dashboard">
      <header className="landlord-hero">
        <p className="landlord-hero__eyebrow">RentalAI Landlord Hub</p>
        <h1 className="landlord-hero__title">Landlord Center</h1>
        <p className="landlord-hero__subtitle">
          Your command centre for listings, guest requests, performance insights,
          and AI-powered listing improvements.
        </p>
      </header>

      <LandlordSummary stats={summary} />
      <LandlordQuickNav />

      <div className="landlord-dashboard__body">
        <section
          id="my-listings"
          className="landlord-section"
          aria-labelledby="my-listings-heading"
        >
          <LandlordSectionHeader
            id="my-listings"
            title="My Listings"
            subtitle={
              listings.length === 0
                ? "No listings on this page."
                : `${listings.length} active listing${listings.length === 1 ? "" : "s"} · mock data`
            }
          />

          {listings.length === 0 ? (
            <p className="landlord-empty card">
              All mock listings were removed. Refresh the page to restore them.
            </p>
          ) : (
            <ul className="landlord-card-grid landlord-card-grid--pair">
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
          className="landlord-section"
          aria-labelledby="booking-requests-heading"
        >
          <LandlordSectionHeader
            id="booking-requests"
            title="Booking Requests"
            subtitle={
              bookingRequests.length === 0
                ? "No booking requests."
                : `${summary.pendingRequests} pending · ${bookingRequests.length} total · mock data`
            }
          />

          {bookingRequests.length === 0 ? (
            <p className="landlord-empty card">No booking requests to show.</p>
          ) : (
            <ul className="landlord-card-grid">
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
          className="landlord-section"
          aria-labelledby="property-performance-heading"
        >
          <LandlordSectionHeader
            id="property-performance"
            title="Property Performance"
            subtitle={`${propertyPerformance.length} propert${propertyPerformance.length === 1 ? "y" : "ies"} tracked · mock data`}
          />

          {topPerforming ? (
            <p className="landlord-callout card" role="status">
              Top performing listing:{" "}
              <strong>{topPerforming.property_title}</strong>
            </p>
          ) : null}

          {propertyPerformance.length === 0 ? (
            <p className="landlord-empty card">No performance data to show.</p>
          ) : (
            <ul className="landlord-card-grid landlord-card-grid--pair">
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
          className="landlord-section"
          aria-labelledby="ai-listing-assistant-heading"
        >
          <LandlordSectionHeader
            id="ai-listing-assistant"
            title="AI Listing Assistant"
            subtitle="Mock tools to optimise descriptions, pricing, and photos — no real AI yet."
          />

          <ul className="landlord-card-grid landlord-card-grid--triple">
            {mockListingAssistantTools.map((feature) => (
              <AiAssistantFeatureCard
                key={feature.id}
                feature={feature}
                onTry={handleTryAiFeature}
              />
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
