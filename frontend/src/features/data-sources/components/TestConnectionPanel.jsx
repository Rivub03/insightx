// src/features/data-sources/components/TestConnectionPanel.jsx
//
// PURPOSE:
//   Renders the "Test Connection" button and its results.
//   This component is intentionally stateless — all state lives in useConnectionTest.
//
// ERROR CATEGORY DISPLAY:
//   Each category maps to an icon + plain-English label so users know what to fix.

import React from "react";

// Maps backend error category strings to human-readable labels with icons
const ERROR_LABELS = {
  AUTH_FAILED: { icon: "🔐", label: "Authentication Failed" },
  HOST_UNREACHABLE: { icon: "🌐", label: "Host Unreachable" },
  TLS_HANDSHAKE_FAILED: { icon: "🔒", label: "TLS Handshake Failed" },
  TIMEOUT: { icon: "⏱️", label: "Connection Timeout" },
  UNSUPPORTED_CONFIG: { icon: "⚙️", label: "Unsupported Configuration" },
  NETWORK_ERROR: { icon: "📡", label: "Network Error" },
  UNKNOWN: { icon: "⚠️", label: "Unknown Error" },
};

/**
 * @param {string}   status    - 'idle' | 'testing' | 'success' | 'failed'
 * @param {Object}   result    - { success, latencyMs, category?, message? } | null
 * @param {Function} onTest    - Called when "Test Connection" is clicked
 * @param {Function} onSave    - Called when "Save Data Source" is clicked
 * @param {boolean}  isSaving  - True while the save request is in flight
 */
function TestConnectionPanel({ status, result, onTest, onSave, isSaving }) {
  const isTesting = status === "testing";
  const canSave = status === "success";

  return (
    <div className="test-panel">
      <h3>Test Your Connection</h3>
      <p className="test-panel__hint">
        Run a connection test before saving. The test is non-destructive — only
        a <code>SELECT 1</code> query is executed.
      </p>

      {/* Test button */}
      <button
        type="button"
        className={`btn btn--test ${isTesting ? "btn--loading" : ""}`}
        onClick={onTest}
        disabled={isTesting}
      >
        {isTesting ? (
          <>
            <Spinner /> Testing...
          </>
        ) : (
          "⚡ Test Connection"
        )}
      </button>

      {/* Result area — only rendered after a test has run */}
      {result && (
        <div
          className={`test-result ${result.success ? "test-result--success" : "test-result--failed"}`}
        >
          {result.success ? (
            // Success
            <p>
              ✅ <strong>Connection successful</strong> — responded in{" "}
              {result.latencyMs}ms
            </p>
          ) : (
            // Failure — show category badge + actionable message
            <>
              <p className="test-result__category">
                {ERROR_LABELS[result.category]?.icon || "⚠️"}
                &nbsp;
                <strong>
                  {ERROR_LABELS[result.category]?.label || result.category}
                </strong>
              </p>
              <p className="test-result__message">{result.message}</p>
            </>
          )}
        </div>
      )}

      {/* Save button — disabled until test passes */}
      <button
        type="button"
        className="btn btn--primary"
        onClick={onSave}
        disabled={!canSave || isSaving}
        title={
          !canSave
            ? "A successful connection test is required before saving."
            : ""
        }
      >
        {isSaving ? (
          <>
            <Spinner /> Saving...
          </>
        ) : (
          "💾 Save Data Source"
        )}
      </button>
    </div>
  );
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export default TestConnectionPanel;
