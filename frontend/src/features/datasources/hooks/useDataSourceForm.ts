import { useState, useEffect } from "react";
import { ENGINE_CONFIG, SupportedEngine } from "@/core/constants/engines";

/**
 * Custom React hook to manage form state and credential configurations
 * for registering new relational OLAP data sources in the InsightX platform.
 */
export function useDataSourceForm() {
  // Tracks the actively selected database engine engine (e.g., oracle, postgresql, mssql)
  const [engine, setEngine] = useState<SupportedEngine>("postgresql");

  // Tracks the network hostname or IP address of the target database server
  const [host, setHost] = useState<string>("");

  // Tracks the connection port number, initialized with the postgresql engine default
  const [port, setPort] = useState<number>(
    ENGINE_CONFIG["postgresql"].defaultPort,
  );

  // Tracks the specific schema, database name, or service identification handle
  const [dbName, setDbName] = useState<string>("");

  // Tracks the chosen access security strategy out of the system's supported auth modes
  const [authMethod, setAuthMethod] = useState<
    "username_password" | "kerberos" | "azure_ad" | "wallet"
  >("username_password");

  /**
   * Synchronizes form configurations dynamically whenever the targeted database engine changes.
   * Automatically replaces unsupported default values when toggling between engines.
   */
  useEffect(() => {
    // Dynamically re-assign the network port to match the selected database default configuration
    setPort(ENGINE_CONFIG[engine].defaultPort);

    // FIX FOR TS2345: Cast the engine-specific configuration array to a wider read-only string array.
    // This allows the `.includes()` invocation to process our broader `authMethod` union type smoothly.
    const supportedAuthOptions = ENGINE_CONFIG[engine]
      .supportedAuth as readonly string[];

    // Check if the current state strategy is valid under the newly active engine configuration rules
    if (!supportedAuthOptions.includes(authMethod)) {
      // Fallback cleanly to the default first entry configuration allowed by that specific database engine
      setAuthMethod(
        ENGINE_CONFIG[engine].supportedAuth[0] as
          | "username_password"
          | "kerberos"
          | "azure_ad"
          | "wallet",
      );
    }
  }, [engine, authMethod]); // Kept dependency tracking active to handle manual configurations securely

  return {
    // Current data source parameter states bundle
    formState: { engine, host, port, dbName, authMethod },
    // Core state updater functions passed up to view controllers
    handlers: { setEngine, setHost, setPort, setDbName, setAuthMethod },
    // Engine validation constants and structural configurations
    engineMeta: ENGINE_CONFIG[engine],
  };
}
