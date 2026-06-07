// src/features/data-sources/hooks/useDataSourceForm.js
//
// PURPOSE:
//   Manages all wizard form state in a single hook.
//   The wizard page (AddDataSourcePage) uses this to read state
//   and pass the right props down to each step component.
//
// STATE SLICES:
//   engine     → which DB type was selected (step 0)
//   connection → host, port, database, name (step 1)
//   auth       → method + credentials (step 2)
//   tls        → enabled, mode, certs (step 3)
//
// KEY DESIGN DECISIONS:
//   1. selectEngine() resets ALL downstream state — changing the engine
//      invalidates auth method choices and TLS labels.
//   2. setAuthMethod() resets ONLY credentials — preserves connection fields.
//      This matches the acceptance criteria in US 107148.
//   3. buildPayload() produces the exact shape the backend expects.

import { useState, useCallback } from "react";
import { ENGINES } from "../constants/engines";

export function useDataSourceForm() {
  const [engine, setEngine] = useState(null);
  const [connection, setConnection] = useState(initialConnection());
  const [auth, setAuth] = useState(initialAuth());
  const [tls, setTls] = useState(initialTls());

  /**
   * Selects an engine and resets all other state to engine-appropriate defaults.
   * Called when the user clicks an engine card in step 0.
   */
  const selectEngine = useCallback((engineKey) => {
    const cfg = ENGINES[engineKey];
    if (!cfg) return;

    setEngine(engineKey);

    // Pre-fill default port — common UX pattern that saves the user a step
    setConnection({
      ...initialConnection(),
      port: cfg.defaultPort,
      oracleConnectionType: cfg.hasConnectionTypeToggle
        ? "service_name"
        : undefined,
    });

    // Default to the first auth method for this engine
    setAuth({
      method: cfg.authMethods[0]?.value || "",
      credentials: {},
    });

    // TLS off by default; pre-load the engine's default mode
    setTls({
      ...initialTls(),
      mode: cfg.tls.defaultMode || "",
    });
  }, []);

  /** Updates a single connection field (host, port, name, database, oracleConnectionType) */
  const updateConnection = useCallback((field, value) => {
    setConnection((prev) => ({ ...prev, [field]: value }));
  }, []);

  /**
   * Switches auth method and clears only the credential fields.
   * Connection fields are intentionally preserved.
   */
  const setAuthMethod = useCallback((method) => {
    setAuth({ method, credentials: {} });
  }, []);

  /** Updates a single credential field */
  const updateCredential = useCallback((field, value) => {
    setAuth((prev) => ({
      ...prev,
      credentials: { ...prev.credentials, [field]: value },
    }));
  }, []);

  /** Toggles TLS on/off; clears file-related fields when disabled */
  const toggleTls = useCallback((enabled) => {
    setTls((prev) => ({
      ...prev,
      enabled,
      ...(enabled ? {} : { caCert: null, clientCert: null, clientKey: null }),
    }));
  }, []);

  /** Updates a single TLS field */
  const updateTls = useCallback((field, value) => {
    setTls((prev) => ({ ...prev, [field]: value }));
  }, []);

  /**
   * Builds the complete payload for the /test or POST / API call.
   * File objects (certs, wallets) are not included here —
   * AddDataSourcePage.jsx uploads them first and substitutes path strings.
   */
  const buildPayload = useCallback(
    () => ({
      engine,
      name: connection.name,
      host: connection.host,
      port: connection.port,
      database: connection.database,
      oracleConnectionType: connection.oracleConnectionType,
      authMethod: auth.method,
      credentials: auth.credentials,
      tls: {
        enabled: tls.enabled,
        verifyServerCert: tls.verifyServerCert,
        mode: tls.mode,
        caCertPath: tls.caCertPath, // populated after upload
        clientCertPath: tls.clientCertPath,
        clientKeyPath: tls.clientKeyPath,
      },
    }),
    [engine, connection, auth, tls],
  );

  return {
    // State (read-only from consumer's perspective)
    engine,
    connection,
    auth,
    tls,
    // Actions
    selectEngine,
    updateConnection,
    setAuthMethod,
    updateCredential,
    toggleTls,
    updateTls,
    buildPayload,
  };
}

// --- Default state factories ---
// Functions (not constants) so each call gets a fresh object (no shared reference issues)

function initialConnection() {
  return {
    name: "",
    host: "",
    port: "",
    database: "",
    oracleConnectionType: "service_name",
  };
}

function initialAuth() {
  return { method: "", credentials: {} };
}

function initialTls() {
  return {
    enabled: false,
    verifyServerCert: true,
    mode: "",
    caCert: null,
    clientCert: null,
    clientKey: null,
    caCertPath: null,
    clientCertPath: null,
    clientKeyPath: null,
  };
}
