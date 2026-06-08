// src/features/data-sources/hooks/useConnectionTest.js
//
// PURPOSE:
//   Manages the state machine for the "Test Connection" flow.
//   Four states: idle → testing → success | failed
//
// IMPORTANT: resetTest() must be called whenever a form field changes AFTER a test.
//   This re-disables the Save button — the user must re-test after any edit.
//   The wizard calls resetTest() inside every onChange handler.

import { useState, useCallback } from "react";
import { testDatasourceConnection } from "../api/datasource.api";

export function useConnectionTest() {
  // 'idle' | 'testing' | 'success' | 'failed'
  const [status, setStatus] = useState("idle");
  // null, or { success, latencyMs, category?, message? }
  const [result, setResult] = useState(null);

  /**
   * Executes the connection test.
   * The payload should be the output of useDataSourceForm's buildPayload(),
   * with any file objects already replaced by server-side paths.
   *
   * @param {Object} payload - Complete datasource config (no File objects)
   */
  const runTest = useCallback(async (payload) => {
    setStatus("testing");
    setResult(null);

    try {
      const data = await testDatasourceConnection(payload);
      setResult(data);
      setStatus(data.success ? "success" : "failed");
    } catch (networkErr) {
      // This path is hit when the InsightX server itself is unreachable,
      // not when the target database is unreachable.
      setResult({
        success: false,
        category: "NETWORK_ERROR",
        message: "Could not reach the InsightX server. Check your network.",
      });
      setStatus("failed");
    }
  }, []);

  /**
   * Resets the test state back to idle.
   * Call this whenever a form field changes after a test has run.
   * This forces re-testing before saving.
   */
  const resetTest = useCallback(() => {
    setStatus("idle");
    setResult(null);
  }, []);

  return {
    status,
    result,
    isTesting: status === "testing",
    isSuccess: status === "success",
    isFailed: status === "failed",
    // canSave is the gatekeeper — Save button only works after a successful test
    canSave: status === "success",
    runTest,
    resetTest,
  };
}
