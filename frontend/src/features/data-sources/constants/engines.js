// src/features/data-sources/constants/engines.js
//
// PURPOSE:
//   Metadata and capabilities configuration for each supported database engine.
//   Used by the frontend to render appropriate form fields, set default ports,
//   and show valid authentication methods.

export const ENGINES = {
  postgresql: {
    label: "PostgreSQL",
    defaultPort: 5432,
    hasConnectionTypeToggle: false,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "ldap", label: "LDAP" }
    ],
    tls: {
      defaultMode: "require",
      modes: [
        { value: "disable", label: "Disable" },
        { value: "allow", label: "Allow" },
        { value: "prefer", label: "Prefer" },
        { value: "require", label: "Require" },
        { value: "verify-ca", label: "Verify CA" },
        { value: "verify-full", label: "Verify Full" }
      ]
    }
  },
  oracle: {
    label: "Oracle 12c+",
    defaultPort: 1521,
    hasConnectionTypeToggle: true,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "wallet", label: "Oracle Wallet" },
      { value: "kerberos", label: "Kerberos" }
    ],
    tls: {
      defaultMode: "ssl",
      modes: [
        { value: "ssl", label: "SSL (TCPS)" }
      ]
    }
  },
  mssql: {
    label: "MS SQL Server",
    defaultPort: 1433,
    hasConnectionTypeToggle: false,
    authMethods: [
      { value: "password", label: "Username & Password" },
      { value: "windows", label: "Windows Authentication" },
      { value: "azure_ad", label: "Azure Active Directory" }
    ],
    tls: {
      defaultMode: "encrypt",
      modes: [
        { value: "encrypt", label: "Encrypt (SSL/TLS)" }
      ]
    }
  }
};
