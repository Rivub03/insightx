"use client";
import { useState } from "react";
import { useDataSourceForm } from "@/features/datasources/hooks/useDataSourceForm";
import { ENGINE_CONFIG, SupportedEngine } from "@/core/constants/engines";

export default function AddDataSourcePage() {
  const { formState, handlers, engineMeta } = useDataSourceForm();
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message?: string;
  } | null>(null);

  const handleTest = async () => {
    setIsTesting(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/sources/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formState),
      });
      const data = await res.json();
      setTestResult({
        success: res.ok,
        message: data.message || data.detail?.error,
      });
    } catch (e) {
      setTestResult({
        success: false,
        message: "Network error connecting to API",
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow-sm border rounded-lg mt-10">
      <h1 className="text-2xl font-bold mb-6">Register Data Source</h1>

      <div className="space-y-4">
        <div>
          <label htmlFor="engine-select" className="block text-sm font-medium">
            Database Engine
          </label>
          <select
            id="engine-select"
            title="Select Database Engine"
            className="w-full border p-2 rounded mt-1"
            value={formState.engine}
            onChange={(e) =>
              handlers.setEngine(e.target.value as SupportedEngine)
            }
          >
            {/* FIX: Explicitly tell TypeScript the types of the mapped array */}
            {(Object.entries(ENGINE_CONFIG) as [string, any][]).map(
              ([key, meta]) => (
                <option key={key} value={key}>
                  {meta.label}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <label htmlFor="host-input" className="block text-sm font-medium">
              Host
            </label>
            <input
              id="host-input"
              title="Database Host Address"
              className="w-full border p-2 rounded mt-1"
              type="text"
              value={formState.host}
              onChange={(e) => handlers.setHost(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="port-input" className="block text-sm font-medium">
              Port
            </label>
            <input
              id="port-input"
              title="Database Port"
              className="w-full border p-2 rounded mt-1"
              type="number"
              value={formState.port}
              onChange={(e) => handlers.setPort(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="pt-4 border-t flex gap-4">
          <button
            onClick={handleTest}
            disabled={isTesting}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          >
            {isTesting ? "Testing..." : "Test Connection"}
          </button>
        </div>

        {testResult && (
          <div
            className={`p-3 rounded ${testResult.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
          >
            {testResult.success ? "✅ " : "❌ "} {testResult.message}
          </div>
        )}
      </div>
    </div>
  );
}
