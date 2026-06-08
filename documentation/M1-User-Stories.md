## Introduction

| Work Item Type | Title                       | State | Effort | Business Value | Value Area | Tags |
| -------------- | --------------------------- | ----- | ------ | -------------- | ---------- | ---- |
| Feature        | M1 — Data Source Onboarding | New   | 20     |                | Business   |      |

### Overview

Enable users to connect and onboard various data sources into the InsightX platform for analytics and querying.

### Scope

- Support for relational databases (PostgreSQL, MySQL, MSSQL, Oracle)
- Support for file uploads (CSV, Excel, JSON)
- REST API / webhook data source connectors
- Connection health check and validation
- Schema auto-discovery and preview
- Secure credential management (encrypted storage)
- Multi-tenant data source isolation

### Acceptance Criteria

- User can connect at least 3 DB types and upload files successfully
- Schema is auto-discovered and displayed on connection
- Invalid credentials show meaningful error messages

## User Stories

### [User Story 107147](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107147): Database Connector Registration (Oracle, PostgreSQL, MS SQL Server)

**User Story** - As a **platform user**, I want to register a new OLAP data source by selecting a database type and providing connection details so that InsightX can query it for analytics.

**Why** - InsightX is an Agentic Reporting Platform — every downstream capability (NL to SQL, Data Dictionary, Insights) depends on a live, registered database connection. Without a clean onboarding flow for the 3 supported engines, the platform cannot function.

**Acceptance Criteria**

- User can select one of 3 supported engines: **Oracle 12c+**, **PostgreSQL**, **MS SQL Server**
- Form captures: Host, Port, Database/Service Name, Username, and engine-specific optional fields (e.g. Oracle SID vs Service Name toggle)
- Each engine has its own field validation rules (e.g. Oracle default port 1521, PG 5432, MSSQL 1433)
- Submitted connection is persisted with a unique name and visible in the data sources list
- Engine icon and type label are displayed on the saved connection card

### [User Story 107148](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107148): Authentication Configuration (Username/Password, Kerberos, Azure AD, Wallet)

**User Story** - As a **platform user**, I want to choose the appropriate authentication method for my database connection so that InsightX can authenticate securely according to my organisation's security policies.

**Why** - Enterprise OLAP databases rarely use simple username/password. Oracle uses Wallets and Kerberos, MS SQL Server supports Windows Auth and Azure AD, and PostgreSQL supports SCRAM-SHA-256 and LDAP. A one-size-fits-all auth form would block adoption across enterprise environments.

**Acceptance Criteria**

- **Oracle 12c+**: supports Username/Password, Oracle Wallet (upload `.sso`/`.p12`), and Kerberos (keytab upload + principal)
- **PostgreSQL**: supports Username/Password (SCRAM-SHA-256), and LDAP/AD pass-through
- **MS SQL Server**: supports SQL Auth (username/password), Windows Integrated Auth, and Azure Active Directory (OAuth2 token flow)
- Auth method selector is shown contextually based on the selected database engine
- Credentials are never stored in plaintext; encrypted at rest using AES-256
- Switching auth method resets only the auth-specific fields, not the connection fields

### [User Story 107149](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107149): TLS/SSL Encryption Configuration for Database Connections

**User Story** - As a **platform user**, I want to configure TLS/SSL encryption on my database connection so that data in transit between InsightX and my database is protected against interception.

**Why** - Enterprise databases are often deployed behind strict network security policies requiring encrypted transport. Without TLS support, InsightX cannot be deployed in regulated environments (e.g. banking, healthcare) where unencrypted DB connections are policy violations.

**Acceptance Criteria**

- TLS toggle (Enable/Disable) is available on all 3 database connector forms
- When enabled, user can upload a CA certificate (`.pem`, `.crt`) for server verification
- Option to upload client certificate and private key for mutual TLS (mTLS)
- `Verify Server Certificate` checkbox (default: on); can be disabled for self-signed certs with a visible warning
- TLS mode labels are engine-aware: **SSL Mode** for PostgreSQL (`require`, `verify-ca`, `verify-full`), **Encrypt** for MS SQL Server, **SSL** for Oracle
- Connection parameters are correctly passed to the underlying JDBC/driver with chosen TLS config

### [User Story 107150](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107150): Connection Test & Validation

**User Story** - As a **platform user**, I want to test my database connection before saving it so that I can immediately confirm whether my credentials, host, port, and TLS settings are correct without having to save and discover errors later.

**Why** - Poor onboarding UX is the[#1](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/1/) reason database integrations fail silently. A test-before-save flow surfaces misconfiguration immediately, reduces support load, and gives the user confidence that the connection is live before committing it to the platform.

**Acceptance Criteria**

- A **"Test Connection"** button is available on the connection form before saving
- Test result shows one of: ✅ Success, ❌ Auth Failed, ❌ Host Unreachable, ❌ TLS Handshake Failed, ❌ Timeout — each with a clear, actionable message
- Test is non-destructive and does not persist any data
- Test respects the currently configured auth method and TLS settings on the form
- Response time is shown (e.g. `Connected in 240ms`)
- If the test fails, the Save button remains disabled with a tooltip explaining why
- Timeout threshold is 10 seconds with a spinner during the test

### [User Story 107151](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107151): Permission-Scoped Object Browser

**User Story** - As a **platform user**, after a successful connection test, I want to see a summary of all database objects (schemas, tables, views) that my authenticated user has permission to access so that I understand the scope of data available to InsightX before saving the data source.

**Why** - In enterprise OLAP environments, a single DB user may have access to dozens of schemas or only a handful of views. Showing the object scope upfront prevents surprises downstream (e.g. NL-to-SQL generating queries against tables the user has no SELECT privilege on), and builds confidence in the connection setup.

**Acceptance Criteria**

- After a successful connection test, an **Object Summary** panel is displayed
- Summary shows counts grouped by type: **Schemas**, **Tables**, **Views**, **Sequences** (where applicable per engine)
- Objects are fetched using the authenticated user's permissions only — no elevation
- Expandable tree allows browsing: Schema → Tables/Views → Column count
- Each object row shows: name, type badge, column count
- A total count banner shows e.g. `3 schemas · 142 tables · 38 views accessible`
- Loading state shown while introspection query runs; handles schemas with 1000+ tables without UI freeze
- Oracle: queries `ALL_TABLES` / `ALL_VIEWS`; PostgreSQL: `information_schema`; MSSQL: `INFORMATION_SCHEMA` with permission checks
