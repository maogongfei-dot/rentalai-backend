/** Area Analysis Center — mock area score (frontend only, no API) */

export const mockAreaScore = {
  postcode: "M1 4BT",
  area_name: "Northern Quarter, Manchester",
  overall_score: 82,
  transport_score: 88,
  safety_score: 74,
  facilities_score: 85,
  school_score: 79,
  rent_value_score: 81,
  summary:
    "A well-connected central neighbourhood with strong daily amenities and good rental demand. Safety scores are moderate — visit at different times and check recent local reports before committing.",
};

export const mockTransportAccess = {
  nearest_bus_stop: "Bedford Road Bus Stop",
  nearest_station: "Bedford Station",
  walking_time_to_station: "12 minutes",
  estimated_commute_to_city_center: "35 minutes",
  transport_rating: 82,
  night_transport_available: true,
  summary:
    "This area has strong public transport access with nearby bus routes, a reachable train station, and reasonable commute time to the city centre.",
};

export const mockLocalAmenities = {
  supermarkets: ["Tesco Express", "Aldi", "Sainsbury's Local"],
  schools: ["Bedford Primary School", "Castle Newnham School"],
  hospitals: ["Bedford Hospital"],
  parks: ["Bedford Park", "Russell Park"],
  gyms: ["PureGym Bedford", "Anytime Fitness"],
  amenities_rating: 78,
  summary:
    "This area offers convenient access to supermarkets, schools, healthcare, parks, and fitness facilities, making it suitable for daily living.",
};

export function getAmenitiesRatingHint(amenitiesRating) {
  if (amenitiesRating >= 80) {
    return {
      label: "Excellent local amenities",
      tone: "excellent",
    };
  }
  if (amenitiesRating >= 60) {
    return {
      label: "Good daily living convenience",
      tone: "good",
    };
  }
  return {
    label: "Limited local amenities",
    tone: "limited",
  };
}

export function getTransportRatingHint(transportRating) {
  if (transportRating >= 80) {
    return {
      label: "Excellent transport",
      tone: "excellent",
    };
  }
  if (transportRating >= 60) {
    return {
      label: "Good transport access",
      tone: "good",
    };
  }
  return {
    label: "Limited transport access",
    tone: "limited",
  };
}

export function getOverallScoreHint(overallScore) {
  if (overallScore >= 80) {
    return {
      label: "Strong rental area",
      tone: "strong",
    };
  }
  if (overallScore >= 60) {
    return {
      label: "Balanced area",
      tone: "balanced",
    };
  }
  return {
    label: "Needs careful review",
    tone: "caution",
  };
}
