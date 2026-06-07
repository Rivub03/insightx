// src/features/data-sources/pages/DataSourceListPage.jsx
//
// PURPOSE:
//   Displays all registered data sources for the current tenant.
//   Each source is shown as a card with engine, name, host, and last test status.
//   Contains an "Add New" button that navigates to the wizard page.
//
// DATA FLOW:
//   On mount → calls listDatasources() API → renders cards
//   On "Add New" click → navigates to /datasources/new (the wizard)

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listDatasources } from "../api/datasource.api.js";
import { ENGINES } from "../constants/engines.js";

function DataSourceListPage() {
  const navigate = useNavigate();

  // Sources fetched from the backend
  const [sources, setSources] = useState([]);
  // Loading state — show spinner while fetching
  const [loading, setLoading] = useState(true);
  // Error state — show message if fetch fails
  const [error, setError] = useState(null);

  // Fetch data sources when the page mounts
  useEffect(() => {
    async function load() {
      try {
        const data = await listDatasources();
        setSources(data);
      } catch (err) {
        setError("Failed to load data sources. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []); // Empty array = run once on mount only

  return (
    <div className="datasource-list-page">
      {/* Page header with title and "Add New" button */}
      <div className="datasource-list-page__header">
        <div>
          <h2>Data Sources</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
            Registered database connections available for querying.
          </p>
        </div>
        <button
          className="btn btn--primary"
          onClick={() => navigate("/datasources/new")}
        >
          + Add Data Source
        </button>
      </div>

      {/* Loading state */}
      {loading && <p className="loading-text">Loading data sources…</p>}

      {/* Error state */}
      {error && <p className="error-banner">{error}</p>}

      {/* Empty state — no sources registered yet */}
      {!loading && !error && sources.length === 0 && (
        <div className="empty-state">
          <div className="empty-state__icon">🗄️</div>
          <h3>No data sources yet</h3>
          <p style={{ marginBottom: "var(--space-lg)" }}>
            Connect your first database to start querying with InsightX.
          </p>
          <button
            className="btn btn--primary"
            onClick={() => navigate("/datasources/new")}
          >
            + Add Your First Data Source
          </button>
        </div>
      )}

      {/* Data source cards grid */}
      {!loading && !error && sources.length > 0 && (
        <div className="datasource-grid">
          {sources.map((source) => (
            <DataSourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   DataSourceCard
   Renders a single data source as a summary card.
   ───────────────────────────────────────────────────────────────────────────── */
function DataSourceCard({ source }) {
  // Look up engine metadata (icon, label) from the constants file
  const engineConfig = ENGINES[source.engine] || {};

  // Map last_test_status to a visual dot colour
  const statusDotClass =
    {
      success: "status-dot--success",
      failed: "status-dot--failed",
    }[source.last_test_status] || "status-dot--unknown";

  const statusLabel =
    {
      success: "Last test passed",
      failed: "Last test failed",
    }[source.last_test_status] || "Not tested";

  return (
    <div className="datasource-card">
      {/* Card header: engine icon + name + engine badge */}
      <div className="datasource-card__header">
        <span className="datasource-card__icon">
          {engineConfig.icon || "🗄️"}
        </span>
        <div>
          <div className="datasource-card__name">{source.name}</div>
          <span className="datasource-card__badge">
            {engineConfig.label || source.engine}
          </span>
        </div>
      </div>

      {/* Connection metadata */}
      <div className="datasource-card__meta">
        <div>
          🔌 {source.host}:{source.port}
        </div>
        <div>🗃️ {source.database_name}</div>
        <div>🔐 {source.auth_method}</div>
        <div>
          <span className={`status-dot ${statusDotClass}`} />
          {statusLabel}
        </div>
        {source.tls_enabled && <div>🔒 TLS enabled</div>}
      </div>
    </div>
  );
}

export default DataSourceListPage;
