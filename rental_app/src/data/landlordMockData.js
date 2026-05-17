/**
 * Landlord Center mock data — frontend only, no API.
 * Replace imports here when wiring real database / API.
 */

export const mockListings = [
  {
    id: "lst-001",
    title: "Bright 2-bed flat near Angel",
    location: "Islington, London",
    price_per_night: 145,
    bedrooms: 2,
    occupancy_rate: 78,
    listing_status: "active",
    views: 342,
    enquiries: 12,
  },
  {
    id: "lst-002",
    title: "Cosy studio with canal views",
    location: "Camden, London",
    price_per_night: 95,
    bedrooms: 0,
    occupancy_rate: 62,
    listing_status: "draft",
    views: 89,
    enquiries: 3,
  },
  {
    id: "lst-003",
    title: "Family home near Victoria Park",
    location: "Hackney, London",
    price_per_night: 210,
    bedrooms: 3,
    occupancy_rate: 91,
    listing_status: "paused",
    views: 518,
    enquiries: 24,
  },
];

export const mockBookingRequests = [
  {
    id: "br-001",
    guest_name: "Emma Watson",
    property_title: "Bright 2-bed flat near Angel",
    check_in: "2026-06-12",
    check_out: "2026-06-18",
    guests: 2,
    message:
      "We're visiting for a wedding nearby. Quiet hours appreciated after 10pm.",
    status: "pending",
  },
  {
    id: "br-002",
    guest_name: "James Chen",
    property_title: "Cosy studio with canal views",
    check_in: "2026-07-01",
    check_out: "2026-07-05",
    guests: 1,
    message: "Solo business trip — early check-in if possible.",
    status: "pending",
  },
  {
    id: "br-003",
    guest_name: "Sofia Martinez",
    property_title: "Family home near Victoria Park",
    check_in: "2026-08-10",
    check_out: "2026-08-17",
    guests: 4,
    message:
      "Family holiday with two children (ages 6 and 9). Happy to provide references.",
    status: "pending",
  },
];

export const mockPropertyPerformance = [
  {
    id: "perf-001",
    property_title: "Bright 2-bed flat near Angel",
    total_views: 342,
    total_enquiries: 12,
    occupancy_rate: 78,
    average_rating: 4.6,
    response_rate: 92,
    performance_score: 81,
  },
  {
    id: "perf-002",
    property_title: "Cosy studio with canal views",
    total_views: 89,
    total_enquiries: 3,
    occupancy_rate: 62,
    average_rating: 4.2,
    response_rate: 75,
    performance_score: 58,
  },
  {
    id: "perf-003",
    property_title: "Family home near Victoria Park",
    total_views: 518,
    total_enquiries: 24,
    occupancy_rate: 91,
    average_rating: 4.9,
    response_rate: 98,
    performance_score: 94,
  },
];

export const mockListingAssistantTools = [
  {
    id: "improve-description",
    title: "Improve Listing Description",
    description:
      "Generate clearer, more attractive listing descriptions.",
  },
  {
    id: "pricing-guidance",
    title: "Pricing Guidance",
    description:
      "Understand whether your nightly price looks competitive.",
  },
  {
    id: "photo-checklist",
    title: "Photo Checklist",
    description:
      "Check whether your listing photos cover the most important areas.",
  },
];
