// src/features/data-sources/api/datasource.api.js
//
// PURPOSE:
//   All fetch() calls to the datasource backend API, in one place.
//   Components and hooks import from here — never call fetch() directly.

const BASE = "/api/v1/datasources";

/**
 * Uploads a single secure file (TLS cert, Oracle Wallet, Kerberos keytab).
 * Returns the server-side path to embed in the datasource payload.
 *
 * @param {File}   file - The File object from a file input
 * @param {string} type - 'ca_cert' | 'client_cert' | 'client_key' | 'wallet' | 'keytab'
 * @returns {Promise<{ path: string, filename: string }>}
 */
export async function uploadSecureFile(file, type) {
  const form = new FormData();
  form.append("file", file);
  form.append("type", type);

  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    credentials: "include", // send session cookie
    body: form,
    // Don't set Content-Type — the browser sets it automatically with boundary for multipart
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "File upload failed");
  }

  return res.json();
}

/**
 * Tests a database connection.
 * Does NOT save anything — purely a validation call.
 *
 * @param {Object} payload - Full datasource config with plaintext credentials
 * @returns {Promise<{ success: boolean, latencyMs: number, category?: string, message?: string }>}
 */
export async function testDatasourceConnection(payload) {
  const res = await fetch(`${BASE}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Test request failed");
  }

  return res.json();
}

/**
 * Creates and saves a new datasource.
 * Call only after a successful test.
 *
 * @param {Object} payload - Full datasource config
 * @returns {Promise<Object>} The saved datasource record (credentials masked)
 */
export async function createDatasource(payload) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Failed to create data source");
  }

  return res.json();
}

/**
 * Fetches all datasources for the current tenant.
 *
 * @returns {Promise<Array>}
 */
export async function listDatasources() {
  const res = await fetch(BASE, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) throw new Error("Failed to fetch data sources");

  const { data } = await res.json();
  return data;
}
