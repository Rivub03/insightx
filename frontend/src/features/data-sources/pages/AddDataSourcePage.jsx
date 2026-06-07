// src/features/data-sources/pages/AddDataSourcePage.jsx
//
// PURPOSE:
//   The main wizard container. Orchestrates all 5 steps and coordinates
//   the form hook, test hook, file uploads, and the final save call.
//
// WIZARD STEPS:
//   0 - EngineSelector:       pick Oracle / PostgreSQL / MSSQL
//   1 - ConnectionDetailsForm: host, port, db name, connection name
//   2 - AuthConfigForm:        auth method + credentials
//   3 - TLSConfigForm:         TLS toggle + cert uploads
//   4 - TestConnectionPanel:   test the connection, then save
//
// FILE UPLOAD FLOW:
//   File inputs in AuthConfigForm and TLSConfigForm store File objects
//   in the form state. Before calling /test or POST /, this page uploads
//   each File to /api/v1/datasources/upload and replaces the File object
//   with the returned server path. This keeps the JSON payload clean.

import React, { useState } from "react";
import { useDataSourceForm } from "../hooks/useDataSourceForm";
import { useConnectionTest } from "../hooks/useConnectionTest";
import { uploadSecureFile, createDatasource } from "../api/datasource.api";
import EngineSelector from "../components/EngineSelector";
import ConnectionDetailsForm from "../components/ConnectionDetailsForm";
import AuthConfigForm from "../components/AuthConfigForm";
import TLSConfigForm from "../components/TLSConfigForm";
import TestConnectionPanel from "../components/TestConnectionPanel";

const STEPS = [
  { label: "Engine", icon: "🗄️" },
  { label: "Connection", icon: "🔌" },
  { label: "Auth", icon: "🔐" },
  { label: "TLS / SSL", icon: "🔒" },
  { label: "Test & Save", icon: "✅" },
];

/**
 * @param {Function} onSuccess - Called with the saved datasource on successful save
 */
function AddDataSourcePage({ onSuccess }) {
  const [step, setStep] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const form = useDataSourceForm();
  const test = useConnectionTest();

  // ---- File upload helper ----

  /**
   * Uploads any File objects in the payload to the server,
   * returning an updated payload with File objects replaced by path strings.
   *
   * @param {Object} payload - buildPayload() output (may contain File objects)
   * @returns {Promise<Object>} Payload with File objects replaced by server paths
   */
  async function resolveFileUploads(payload) {
    // Work on a shallow copy — don't mutate the original
    const p = {
      ...payload,
      credentials: { ...payload.credentials },
      tls: { ...payload.tls },
    };

    // Oracle Wallet file
    if (p.credentials.walletFile instanceof File) {
      const { path } = await uploadSecureFile(
        p.credentials.walletFile,
        "wallet",
      );
      p.credentials.walletLocation = path;
      delete p.credentials.walletFile; // remove File object — not JSON-serialisable
      delete p.credentials.walletFileName;
    }

    // Kerberos keytab
    if (p.credentials.keytabFile instanceof File) {
      const { path } = await uploadSecureFile(
        p.credentials.keytabFile,
        "keytab",
      );
      p.credentials.keytabPath = path;
      delete p.credentials.keytabFile;
      delete p.credentials.keytabFileName;
    }

    // TLS CA cert
    if (p.tls.caCert instanceof File) {
      const { path } = await uploadSecureFile(p.tls.caCert, "ca_cert");
      p.tls.caCertPath = path;
      delete p.tls.caCert;
    }

    // mTLS client cert and key
    if (p.tls.clientCert instanceof File) {
      const { path } = await uploadSecureFile(p.tls.clientCert, "client_cert");
      p.tls.clientCertPath = path;
      delete p.tls.clientCert;
    }

    if (p.tls.clientKey instanceof File) {
      const { path } = await uploadSecureFile(p.tls.clientKey, "client_key");
      p.tls.clientKeyPath = path;
      delete p.tls.clientKey;
    }

    return p;
  }

  // ---- Wizard actions ----

  async function handleTest() {
    const payload = form.buildPayload();
    const resolvedPayload = await resolveFileUploads(payload);
    test.runTest(resolvedPayload);
  }

  async function handleSave() {
    if (!test.canSave) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const payload = form.buildPayload();
      const saved = await createDatasource(payload);
      if (onSuccess) onSuccess(saved);
    } catch (err) {
      setSaveError(err.message || "Save failed. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  /**
   * Determines whether the "Next" button should be enabled for the current step.
   * Keeps validation light — just checks required fields are non-empty.
   */
  function canAdvance() {
    const { engine, connection, auth } = form;
    if (step === 0) return !!engine;
    if (step === 1)
      return !!(
        connection.name &&
        connection.host &&
        connection.port &&
        connection.database
      );
    if (step === 2) return !!auth.method;
    return true; // TLS and test steps are always advanceable
  }

  // ---- Render ----

  return (
    <div className="wizard-page">
      {/* Step progress indicator */}
      <StepIndicator steps={STEPS} current={step} />

      {/* Step content */}
      <div className="wizard-body">
        {step === 0 && (
          <EngineSelector
            selected={form.engine}
            onSelect={(key) => {
              form.selectEngine(key);
              test.resetTest();
            }}
          />
        )}

        {step === 1 && (
          <ConnectionDetailsForm
            engine={form.engine}
            values={form.connection}
            onChange={(f, v) => {
              form.updateConnection(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 2 && (
          <AuthConfigForm
            engine={form.engine}
            method={form.auth.method}
            credentials={form.auth.credentials}
            onMethodChange={(m) => {
              form.setAuthMethod(m);
              test.resetTest();
            }}
            onCredentialChange={(f, v) => {
              form.updateCredential(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 3 && (
          <TLSConfigForm
            engine={form.engine}
            tls={form.tls}
            onToggle={(v) => {
              form.toggleTls(v);
              test.resetTest();
            }}
            onChange={(f, v) => {
              form.updateTls(f, v);
              test.resetTest();
            }}
          />
        )}

        {step === 4 && (
          <TestConnectionPanel
            status={test.status}
            result={test.result}
            onTest={handleTest}
            onSave={handleSave}
            isSaving={isSaving}
          />
        )}

        {saveError && <p className="error-banner">{saveError}</p>}
      </div>

      {/* Navigation */}
      <div className="wizard-nav">
        {step > 0 && (
          <button type="button" onClick={() => setStep((s) => s - 1)}>
            ← Back
          </button>
        )}
        {step < 4 && (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance()}
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}

// Simple step progress indicator component
function StepIndicator({ steps, current }) {
  return (
    <ol className="step-indicator">
      {steps.map((step, i) => (
        <li
          key={i}
          className={`step-indicator__item ${i === current ? "active" : ""} ${i < current ? "done" : ""}`}
          aria-current={i === current ? "step" : undefined}
        >
          <span>{step.icon}</span>
          <span>{step.label}</span>
        </li>
      ))}
    </ol>
  );
}

export default AddDataSourcePage;
