const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchShortRentRecommendations() {
  const res = await fetch(
    `${API_BASE_URL}/api/short-rent/recommendations`,
    { method: "GET" }
  );
  return res.json();
}

export async function createShortRentListing(data) {
  const res = await fetch(`${API_BASE_URL}/api/short-rent/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}
