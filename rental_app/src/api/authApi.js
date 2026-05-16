/**
 * Auth API — register / login.
 * Base URL from VITE_API_BASE_URL; dev falls back to same-origin /api (Vite proxy).
 */

const API_BASE_RAW = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL =
  typeof API_BASE_RAW === "string" ? API_BASE_RAW.replace(/\/+$/, "") : "";

function authUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

function loginUrl() {
  return authUrl("/api/auth/login");
}

function registerUrl() {
  return authUrl("/api/auth/register");
}

async function parseErrorDetail(res, fallback) {
  let detail = fallback;
  try {
    const errBody = await res.json();
    if (typeof errBody.detail === "string") {
      detail = errBody.detail;
    } else if (errBody.detail) {
      detail = String(errBody.detail);
    } else if (errBody.message) {
      detail = String(errBody.message);
    }
  } catch {
    try {
      const text = await res.text();
      if (text) detail = text.slice(0, 200);
    } catch {
      /* ignore */
    }
  }
  return detail;
}

/**
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ access_token: string, token_type: string }>}
 */
export async function loginUser(email, password) {
  const normalizedEmail = String(email ?? "").trim();
  const pwd = String(password ?? "");

  if (!normalizedEmail || !pwd) {
    throw new Error("Email and password are required.");
  }

  let res;
  try {
    res = await fetch(loginUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail, password: pwd }),
    });
  } catch (err) {
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(
      `Login request failed (network error): ${cause}`,
      { cause: err instanceof Error ? err : undefined }
    );
  }

  if (!res.ok) {
    throw new Error(
      await parseErrorDetail(res, `Login failed (HTTP ${res.status})`)
    );
  }

  let data;
  try {
    data = await res.json();
  } catch (err) {
    throw new Error("Login response was not valid JSON", {
      cause: err instanceof Error ? err : undefined,
    });
  }

  if (!data?.access_token) {
    throw new Error("Login response missing access_token.");
  }

  return {
    access_token: data.access_token,
    token_type: data.token_type || "bearer",
  };
}

/**
 * @param {{ email: string, password: string, full_name?: string | null }} payload
 * @returns {Promise<{ id: number, email: string, full_name: string | null, is_active: boolean, created_at: string }>}
 */
export async function registerUser({ email, password, full_name }) {
  const normalizedEmail = String(email ?? "").trim();
  const pwd = String(password ?? "");
  const name =
    full_name === undefined || full_name === null
      ? null
      : String(full_name).trim() || null;

  if (!normalizedEmail || !pwd) {
    throw new Error("Email and password are required.");
  }

  let res;
  try {
    res = await fetch(registerUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: normalizedEmail,
        password: pwd,
        full_name: name,
      }),
    });
  } catch (err) {
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(
      `Registration request failed (network error): ${cause}`,
      { cause: err instanceof Error ? err : undefined }
    );
  }

  if (!res.ok) {
    throw new Error(
      await parseErrorDetail(res, `Registration failed (HTTP ${res.status})`)
    );
  }

  let data;
  try {
    data = await res.json();
  } catch (err) {
    throw new Error("Registration response was not valid JSON", {
      cause: err instanceof Error ? err : undefined,
    });
  }

  return data;
}
