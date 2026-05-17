import { useCallback, useMemo, useState } from "react";
import {
  mockBookingRequests,
  mockListingAssistantTools,
  mockListings,
  mockPropertyPerformance,
} from "../data/landlordMockData.js";

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

/**
 * Landlord Center state — mock/static data today; swap loaders for API later.
 */
export function useLandlordDashboardState() {
  const [listings, setListings] = useState(() => [...mockListings]);
  const [bookingRequests, setBookingRequests] = useState(() => [
    ...mockBookingRequests,
  ]);

  const propertyPerformance = mockPropertyPerformance;
  const listingAssistantTools = mockListingAssistantTools;

  const topPerforming = useMemo(
    () => getTopPerformingListing(propertyPerformance),
    [propertyPerformance],
  );

  const summary = useMemo(
    () =>
      computeDashboardSummary(listings, bookingRequests, propertyPerformance),
    [listings, bookingRequests, propertyPerformance],
  );

  const handleEditListing = useCallback((listing) => {
    console.log("Edit listing:", listing.id, listing);
  }, []);

  const handleRemoveListing = useCallback((id) => {
    setListings((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handleUpdateBookingStatus = useCallback((id, status) => {
    if (status !== "accepted" && status !== "declined" && status !== "pending") {
      return;
    }
    setBookingRequests((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status } : item)),
    );
  }, []);

  const handleTryAssistantTool = useCallback((tool) => {
    console.log("AI Listing Assistant:", tool.id, tool.title);
  }, []);

  return {
    listings,
    bookingRequests,
    propertyPerformance,
    listingAssistantTools,
    summary,
    topPerforming,
    handleEditListing,
    handleRemoveListing,
    handleUpdateBookingStatus,
    handleTryAssistantTool,
  };
}
