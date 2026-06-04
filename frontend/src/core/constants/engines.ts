// Define constant metadata for all supported engines
export const ENGINE_CONFIG = {
  postgresql: {
    label: "PostgreSQL",
    defaultPort: 5432,
    tlsLabel: "SSL Mode",
    supportedAuth: ["username_password"],
  },
  oracle: {
    label: "Oracle 12c+",
    defaultPort: 1521,
    tlsLabel: "SSL",
    supportedAuth: ["username_password", "oracle_wallet", "kerberos"],
  },
  mssql: {
    label: "MS SQL Server",
    defaultPort: 1433,
    tlsLabel: "Encrypt",
    supportedAuth: ["username_password", "azure_ad"],
  },
} as const;

export type SupportedEngine = keyof typeof ENGINE_CONFIG;
