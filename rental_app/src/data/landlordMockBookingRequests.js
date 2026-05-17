/** Mock landlord booking requests — frontend only, no API */
export const MOCK_LANDLORD_BOOKING_REQUESTS = [
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
