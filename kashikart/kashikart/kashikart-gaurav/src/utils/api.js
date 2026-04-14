export const DEFAULT_TIMEOUT_MS = 60000;

const AUTH_TOKEN_KEYS = ["kashikart_token", "access_token"];
let hasTriggeredAuthRedirect = false;

function getAuthToken() {
  for (const key of AUTH_TOKEN_KEYS) {
    const token = localStorage.getItem(key);
    if (token) return token;
  }
  return null;
}

function clearAuthTokens() {
  AUTH_TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
}

function handleUnauthorized() {
  clearAuthTokens();

  if (hasTriggeredAuthRedirect) return;
  hasTriggeredAuthRedirect = true;

  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export function getErrorMessage(error, fallback = "Something went wrong.") {
  if (!error) return fallback;
  if (typeof error === "string") return error;
  return error.message || fallback;
}

function isRetryableStatus(status) {
  if (typeof status !== "number") return true;
  return status >= 500;
}

export async function requestJson(url, options = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers = {}, ...rest } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const token = getAuthToken();
  const mergedHeaders = { ...headers };

  // Most callers send JSON string bodies; add header automatically when omitted.
  if (
    rest.body &&
    typeof rest.body === "string" &&
    !mergedHeaders["Content-Type"] &&
    !mergedHeaders["content-type"]
  ) {
    mergedHeaders["Content-Type"] = "application/json";
  }

  if (token) {
    mergedHeaders["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, { ...rest, headers: mergedHeaders, signal: controller.signal });
    const contentType = response.headers.get("content-type") || "";
    const raw = await response.text();

    let data;
    if (contentType.includes("application/json")) {
      // Handle empty bodies (e.g., 204 No Content) gracefully
      data = raw ? JSON.parse(raw) : null;
    } else {
      data = raw;
    }

    if (!response.ok) {
      const validationMessage = Array.isArray(data?.detail)
        ? data.detail
            .map((item) => item?.msg)
            .filter(Boolean)
            .join("; ")
        : "";

      const message =
        (typeof data === "string" && data.trim()) ||
        data?.message ||
        data?.detail ||
        validationMessage ||
        "";
      const error = new Error(message || `Request failed (${response.status})`);
      error.status = response.status;
      error.data = data;

      if (response.status === 401) {
        handleUnauthorized();
      }

      throw error;
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function requestWithRetry(
  requestFn,
  { retries = 2, baseDelayMs = 500, shouldRetry } = {}
) {
  let attempt = 0;
  let lastError;

  while (attempt <= retries) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;
      const retryAllowed =
        typeof shouldRetry === "function"
          ? shouldRetry(error)
          : isRetryableStatus(error?.status);

      if (!retryAllowed || attempt === retries) {
        throw error;
      }

      const delay = baseDelayMs * Math.pow(2, attempt);
      await new Promise((resolve) => setTimeout(resolve, delay));
      attempt += 1;
    }
  }

  throw lastError;
}
