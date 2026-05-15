/**
 * AI Chat — HTTP client for POST /api/ai-chat.
 * Expected JSON: { answer: string, intent: string, suggested_next_actions: array }
 */

const API_BASE_RAW = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof API_BASE_RAW === "string" ? API_BASE_RAW.replace(/\/+$/, "") : "";

function chatUrl() {
  return API_BASE_URL ? `${API_BASE_URL}/api/ai-chat` : "/api/ai-chat";
}

/**
 * @param {string} message
 * @returns {Promise<{ answer: string, intent: string, suggested_next_actions: unknown[] }>}
 */
export async function sendAIChatMessage(message) {
  const trimmed = String(message ?? "").trim();
  if (!trimmed) {
    throw new Error("Message cannot be empty");
  }

  const url = chatUrl();

  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: trimmed }),
    });
  } catch (err) {
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(
      `AI chat request failed (no response or network error): ${cause}`,
      { cause: err instanceof Error ? err : undefined }
    );
  }

  if (!res.ok) {
    let detail = "";
    try {
      const errBody = await res.text();
      if (errBody) detail = ` — ${errBody.slice(0, 200)}`;
    } catch {
      /* ignore body read errors */
    }
    throw new Error(
      `AI chat request failed: HTTP ${res.status} ${res.statusText}${detail}`
    );
  }

  let data;
  try {
    data = await res.json();
  } catch (err) {
    throw new Error("AI chat response was not valid JSON", {
      cause: err instanceof Error ? err : undefined,
    });
  }

  return {
    answer: typeof data.answer === "string" ? data.answer : "",
    intent: typeof data.intent === "string" ? data.intent : "",
    suggested_next_actions: Array.isArray(data.suggested_next_actions)
      ? data.suggested_next_actions
      : [],
  };
}
