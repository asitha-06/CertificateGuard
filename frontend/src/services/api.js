
const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${BASE_URL}${path}`, options);
    } catch (err) {
    console.error("API NETWORK ERROR:", {
      url: `${BASE_URL}${path}`,
      errorName: err?.name,
      errorMessage: err?.message,
    });

    throw new Error(
      `Network request failed: ${err?.message || "Unknown connection error"}`
    );
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || `Request failed (${response.status})`
    );
  }

  return data;
}

export const api = {
  health: () => request("/api/health"),

  contractInfo: () => request("/api/contract-info"),

  history: () => request("/api/history"),

  verify: (file, registrationNumber) => {
    const form = new FormData();

    form.append("file", file);

    if (registrationNumber?.trim()) {
      form.append("registration_number", registrationNumber.trim());
    }

    return request("/api/verify", {
      method: "POST",
      body: form,
    });
  },
};

export { BASE_URL };
