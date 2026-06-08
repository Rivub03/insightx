import React from "react";
import { ENGINES } from "../constants/engines";

function EngineSelector({ selected, onSelect }) {
  const engines = [
    { key: "postgresql", icon: "🐘" },
    { key: "oracle", icon: "🦴" },
    { key: "mssql", icon: "⚙️" },
  ];

  return (
    <div className="engine-selector">
      <h2>Select Database Engine</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Choose the type of database you want to connect to.
      </p>
      <div className="engine-grid">
        {engines.map(({ key, icon }) => {
          const config = ENGINES[key];
          return (
            <button
              key={key}
              className={`engine-card ${selected === key ? "engine-card--selected" : ""}`}
              onClick={() => onSelect(key)}
              type="button"
            >
              <div className="engine-card__icon">{icon}</div>
              <div className="engine-card__label">{config.label}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default EngineSelector;
