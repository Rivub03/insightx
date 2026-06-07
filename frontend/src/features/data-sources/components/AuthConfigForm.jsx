import React from "react";
import { ENGINES } from "../constants/engines";

function AuthConfigForm({
  engine,
  method,
  credentials,
  onMethodChange,
  onCredentialChange,
}) {
  const config = ENGINES[engine] || {};
  const authMethods = config.authMethods || [];

  return (
    <div className="auth-form">
      <h2>Authentication</h2>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-lg)" }}>
        Choose an authentication method and provide the necessary credentials.
      </p>

      {/* Auth method tabs */}
      <div className="auth-method-tabs">
        {authMethods.map((m) => (
          <button
            key={m.value}
            type="button"
            className={`auth-tab ${method === m.value ? "auth-tab--active" : ""}`}
            onClick={() => onMethodChange(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Credential forms per auth method */}
      <div className="auth-credentials">
        {method === "password" && (
          <PasswordForm
            engine={engine}
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "wallet" && (
          <WalletForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "kerberos" && (
          <KerberosForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "windows" && (
          <WindowsAuthForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "azure_ad" && (
          <AzureADForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
        {method === "ldap" && (
          <LDAPForm
            credentials={credentials}
            onCredentialChange={onCredentialChange}
          />
        )}
      </div>
    </div>
  );
}

function PasswordForm({ engine, credentials, onCredentialChange }) {
  return (
    <>
      {engine === "oracle" && (
        <div className="auth-note">
          💡 Oracle database login: enter your database username and password.
        </div>
      )}
      <div className="form-field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="e.g., dbuser"
          value={credentials.username || ""}
          onChange={(e) => onCredentialChange("username", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="••••••••"
          value={credentials.password || ""}
          onChange={(e) => onCredentialChange("password", e.target.value)}
        />
      </div>
    </>
  );
}

function WalletForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Upload your Oracle Wallet file (.sso or .p12). Your database credentials
        will be securely encrypted and stored.
      </div>
      <div className="form-field">
        <label htmlFor="walletFile">Oracle Wallet File</label>
        <input
          id="walletFile"
          type="file"
          accept=".sso,.p12"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onCredentialChange("walletFile", file);
              onCredentialChange("walletFileName", file.name);
            }
          }}
        />
        <div className="field-hint">
          {credentials.walletFileName || "Select a .sso or .p12 wallet file"}
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="walletPassword">Wallet Password</label>
        <input
          id="walletPassword"
          type="password"
          placeholder="••••••••"
          value={credentials.walletPassword || ""}
          onChange={(e) => onCredentialChange("walletPassword", e.target.value)}
        />
        <div className="field-hint">Leave empty if your wallet has no password</div>
      </div>
    </>
  );
}

function KerberosForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Kerberos authentication requires a keytab file and principal name.
      </div>
      <div className="form-field">
        <label htmlFor="keytabFile">Kerberos Keytab File</label>
        <input
          id="keytabFile"
          type="file"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onCredentialChange("keytabFile", file);
              onCredentialChange("keytabFileName", file.name);
            }
          }}
        />
        <div className="field-hint">
          {credentials.keytabFileName || "Select your keytab file"}
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="principal">Principal</label>
        <input
          id="principal"
          type="text"
          placeholder="e.g., user@REALM.COM"
          value={credentials.principal || ""}
          onChange={(e) => onCredentialChange("principal", e.target.value)}
        />
        <div className="field-hint">Kerberos principal (user@REALM)</div>
      </div>
    </>
  );
}

function WindowsAuthForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Windows Integrated Authentication uses your system credentials. This only
        works when the backend is running on a Windows host in the same domain.
      </div>
      <div className="form-field">
        <label htmlFor="domain">Domain (optional)</label>
        <input
          id="domain"
          type="text"
          placeholder="e.g., CORP"
          value={credentials.domain || ""}
          onChange={(e) => onCredentialChange("domain", e.target.value)}
        />
        <div className="field-hint">Leave empty to use the local machine</div>
      </div>
    </>
  );
}

function AzureADForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 Azure AD authentication requires you to log in with your Azure credentials.
      </div>
      <div className="form-field">
        <label htmlFor="tenantId">Tenant ID</label>
        <input
          id="tenantId"
          type="text"
          placeholder="e.g., xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={credentials.tenantId || ""}
          onChange={(e) => onCredentialChange("tenantId", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="clientId">Client ID</label>
        <input
          id="clientId"
          type="text"
          placeholder="e.g., xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={credentials.clientId || ""}
          onChange={(e) => onCredentialChange("clientId", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="clientSecret">Client Secret</label>
        <input
          id="clientSecret"
          type="password"
          placeholder="••••••••"
          value={credentials.clientSecret || ""}
          onChange={(e) => onCredentialChange("clientSecret", e.target.value)}
        />
      </div>
    </>
  );
}

function LDAPForm({ credentials, onCredentialChange }) {
  return (
    <>
      <div className="auth-note">
        💡 LDAP authentication: your credentials will be passed to the LDAP server.
      </div>
      <div className="form-field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          placeholder="e.g., john.doe"
          value={credentials.username || ""}
          onChange={(e) => onCredentialChange("username", e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="••••••••"
          value={credentials.password || ""}
          onChange={(e) => onCredentialChange("password", e.target.value)}
        />
      </div>
    </>
  );
}

export default AuthConfigForm;
