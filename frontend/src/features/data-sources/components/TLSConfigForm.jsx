import React from "react";
import { ENGINES } from "../constants/engines";

function TLSConfigForm({ engine, tls, onToggle, onChange }) {
  const config = ENGINES[engine] || {};
  const tlsModes = config.tls?.modes || [];

  return (
    <div className="tls-form">
      <h2>TLS / SSL Configuration</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Encrypt your database connection and verify the server's certificate.
      </p>

      {/* TLS toggle */}
      <div className="form-field form-field--inline">
        <input
          id="tlsToggle"
          type="checkbox"
          checked={tls.enabled || false}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <label htmlFor="tlsToggle" style={{ marginBottom: 0 }}>
          Enable TLS / SSL Encryption
          <span className="toggle-hint"> – recommended for production</span>
        </label>
      </div>

      {tls.enabled && (
        <>
          {/* TLS Mode */}
          {tlsModes.length > 0 && (
            <div className="form-field">
              <label htmlFor="tlsMode">
                {engine === "postgresql"
                  ? "SSL Mode"
                  : engine === "mssql"
                    ? "Encrypt"
                    : "SSL Mode"}
              </label>
              <select
                id="tlsMode"
                value={tls.mode || ""}
                onChange={(e) => onChange("mode", e.target.value)}
              >
                <option value="">Select mode…</option>
                {tlsModes.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Verify Server Certificate */}
          <div className="form-field form-field--inline">
            <input
              id="verifyCert"
              type="checkbox"
              checked={tls.verifyServerCert !== false}
              onChange={(e) => onChange("verifyServerCert", e.target.checked)}
            />
            <label htmlFor="verifyCert" style={{ marginBottom: 0 }}>
              Verify Server Certificate
            </label>
          </div>

          {!tls.verifyServerCert && (
            <div className="warning-banner">
              ⚠️ <strong>Security Risk:</strong> You are skipping certificate verification. This
              leaves your connection vulnerable to man-in-the-middle attacks. Only disable
              verification for testing with self-signed certificates — never in production.
            </div>
          )}

          {/* CA Certificate Upload */}
          {tls.verifyServerCert && (
            <div className="form-field">
              <label htmlFor="caCert">CA Certificate (optional)</label>
              <input
                id="caCert"
                type="file"
                accept=".pem,.crt,.cer"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("caCert", file);
                }}
              />
              <div className="field-hint">
                {tls.caCert?.name || "Upload a .pem or .crt file if using a custom CA"}
              </div>
            </div>
          )}

          {/* mTLS: Client Certificate and Key */}
          <div style={{ marginTop: "var(--space-lg)", paddingTop: "var(--space-lg)", borderTop: "1px solid var(--color-border)" }}>
            <h3>Mutual TLS (mTLS) – Optional</h3>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
              Upload client certificate and key for mutual TLS authentication.
            </p>

            <div className="form-field">
              <label htmlFor="clientCert">Client Certificate</label>
              <input
                id="clientCert"
                type="file"
                accept=".pem,.crt,.cer"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("clientCert", file);
                }}
              />
              <div className="field-hint">
                {tls.clientCert?.name || "Upload your client certificate (.pem or .crt)"}
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="clientKey">Client Key</label>
              <input
                id="clientKey"
                type="file"
                accept=".pem,.key"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onChange("clientKey", file);
                }}
              />
              <div className="field-hint">
                {tls.clientKey?.name || "Upload your private key (.pem or .key)"}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default TLSConfigForm;
