import React from "react";
import { ENGINES } from "../constants/engines";

function ConnectionDetailsForm({ engine, values, onChange }) {
  const config = ENGINES[engine] || {};

  return (
    <div>
      <h2>Connection Details</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Enter the connection information for your {config.label} database.
      </p>

      <form>
        {/* Connection Name */}
        <div className="form-field">
          <label htmlFor="name">Connection Name</label>
          <input
            id="name"
            type="text"
            placeholder="e.g., Production Warehouse"
            value={values.name || ""}
            onChange={(e) => onChange("name", e.target.value)}
          />
          <div className="field-hint">A friendly name for this connection</div>
        </div>

        {/* Host */}
        <div className="form-field">
          <label htmlFor="host">Host</label>
          <input
            id="host"
            type="text"
            placeholder="e.g., db.example.com or 192.168.1.100"
            value={values.host || ""}
            onChange={(e) => onChange("host", e.target.value)}
          />
          <div className="field-hint">Hostname or IP address</div>
        </div>

        {/* Port */}
        <div className="form-field">
          <label htmlFor="port">Port</label>
          <input
            id="port"
            type="number"
            placeholder={`Default: ${config.defaultPort || 5432}`}
            value={values.port || ""}
            onChange={(e) => onChange("port", parseInt(e.target.value, 10) || "")}
          />
          <div className="field-hint">
            Default: {config.defaultPort || "see your DB documentation"}
          </div>
        </div>

        {/* Database / Service Name */}
        <div className="form-field">
          <label htmlFor="database">
            {engine === "oracle" ? "Service Name / SID" : "Database Name"}
          </label>
          <input
            id="database"
            type="text"
            placeholder={engine === "oracle" ? "e.g., ORCL or FREE" : "e.g., postgres"}
            value={values.database || ""}
            onChange={(e) => onChange("database", e.target.value)}
          />
        </div>

        {/* Oracle Connection Type Toggle (SID vs Service Name) */}
        {config.hasConnectionTypeToggle && (
          <div className="form-field">
            <label>Connection Type</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="connectionType"
                  value="service_name"
                  checked={values.oracleConnectionType === "service_name"}
                  onChange={(e) => onChange("oracleConnectionType", e.target.value)}
                />
                Service Name
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="connectionType"
                  value="sid"
                  checked={values.oracleConnectionType === "sid"}
                  onChange={(e) => onChange("oracleConnectionType", e.target.value)}
                />
                SID
              </label>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

export default ConnectionDetailsForm;
