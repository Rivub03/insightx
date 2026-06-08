## [Feature 107125](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107125): M1 — Data Source Onboarding

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

- User can connect at least 3 DB types and upload files successfully. More DB types will come in later updates.
- Schema is auto-discovered and displayed on connection
- Invalid credentials show meaningful error messages

## [Feature 107126](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107126): M2 — Data Dictionary Generation

### Overview

Automatically generate and maintain a human-readable data dictionary from connected data sources to support NL-to-SQL accuracy and user understanding.

### Scope

- Auto-generate table/column descriptions from schema metadata
- AI-assisted column description enrichment
- Manual override and annotation support
- Tag and categorize columns (PII, sensitive, dimension, measure)
- Version history for dictionary changes
- Export data dictionary as PDF/Excel

### Acceptance Criteria

- Dictionary is auto-populated on data source connection
- Users can edit and annotate any field
- PII fields are flagged correctly

## [Feature 107127](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107127): M3 — NL to SQL Generation

### Overview

Allow users to query connected data sources using plain natural language, which is translated to SQL and executed in real-time.

### Scope

- Natural language input interface
- LLM-powered NL-to-SQL translation (context-aware using data dictionary)
- SQL preview and manual edit before execution
- Query execution engine with result rendering (table, chart)
- Query error handling and user-friendly feedback
- Support for multi-table joins and aggregations
- Query optimization hints

### Acceptance Criteria

- 85%+ accuracy on standard business queries
- SQL is shown to user before execution
- Results render in both tabular and chart format

## [Feature 107128](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107128): M4 — Create Insight

### Overview

Enable users to build, configure, and save insights (visualizations + queries) from NL or SQL queries.

### Scope

- Insight builder with chart type selection (bar, line, pie, table, KPI card)
- Drag-and-drop layout configuration
- Insight naming, description, and tagging
- Save as draft or publish
- Link insight to a data source and query
- Support for calculated fields and filters
- Preview before publish

### Acceptance Criteria

- User can create and publish an insight in under 5 steps
- At least 5 chart types are supported
- Draft insights are auto-saved

## [Feature 107129](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107129): M5 — Insight History & Versioning

### Overview

Track and manage the history of changes to insights, allowing users to review, compare, and restore previous versions.

### Scope

- Automatic version snapshot on each save/publish
- Version timeline view with author and timestamp
- Side-by-side version comparison
- Restore to any previous version
- Change log with diff highlighting (query/config changes)
- Audit trail for compliance

### Acceptance Criteria

- Every save creates a versioned snapshot
- User can restore any version within 30 seconds
- Diff view clearly highlights changes

## [Feature 107130](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107130): M6 — Export Insight

### Overview

Allow users to export insights and their underlying data in multiple formats for sharing and reporting.

### Scope

- Export chart/visualization as PNG, SVG, PDF
- Export underlying data as CSV, Excel, JSON
- Scheduled export via email
- Shareable public/private link generation
- Embed code generation (iframe widget)
- Watermarking and branding options

### Acceptance Criteria

- Export in all listed formats completes in under 10 seconds
- Scheduled exports are delivered reliably
- Shared links respect access permissions

## [Feature 107131](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107131): M7 — Notifications & Alerts

### Overview

Provide proactive alerting and notification capabilities when data thresholds are met or scheduled events occur.

### Scope

- Threshold-based alerts (e.g., value > X)
- Scheduled data refresh notifications
- In-app notification center
- Email and webhook notification channels
- Alert history and acknowledgement
- Snooze and mute options per alert
- Role-based alert subscription management

### Acceptance Criteria

- Alerts trigger within 2 minutes of threshold breach
- Users receive notifications via at least 2 channels
- Alert history is retained for 90 days

## [Feature 107132](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107132): M8 — Tools Glossary

### Overview

Provide a searchable, curated glossary of business terms, metrics, and KPIs to improve NL query accuracy and user understanding.

### Scope

- Admin-managed glossary with term, definition, synonyms
- Link glossary terms to data dictionary fields
- Contextual glossary suggestions in NL input
- Full-text search across glossary
- Import/export glossary (CSV/JSON)
- Versioning of glossary terms

### Acceptance Criteria

- Glossary terms appear as suggestions during NL query input
- Admins can import 100+ terms via CSV
- Search returns results in under 1 second

## [Feature 107133](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107133): M9 — Model Configuration (Cloud & On-Prem)

### Overview

Allow platform administrators to configure and manage the underlying LLM models used for NL-to-SQL, supporting both cloud-based and on-premises deployments.

### Scope

- Cloud LLM provider configuration (OpenAI, Azure OpenAI, Anthropic, Google Gemini)
- On-premises model support (Ollama, LM Studio, self-hosted)
- Model selection per use-case (NL-to-SQL, description generation, etc.)
- API key and endpoint management (encrypted)
- Model performance benchmarking UI
- Fallback model configuration
- Token usage tracking and budget alerts

### Acceptance Criteria

- At least 2 cloud and 1 on-prem provider configurable
- Model switch takes effect without system restart
- Token usage visible in real-time dashboard

## [Feature 107134](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107134): M10 — Authentication & Authorization (RBAC / ABAC):

### Overview

Implement a robust authentication and authorization system supporting role-based and attribute-based access control across the platform.

### Scope

- SSO integration (SAML 2.0, OAuth 2.0, OpenID Connect)
- Local username/password authentication with MFA
- Role-Based Access Control (RBAC): Admin, Analyst, Viewer roles
- Attribute-Based Access Control (ABAC): data-level row/column restrictions
- Permission matrix management UI
- Session management and token expiry
- Audit log for authentication events
- API key management for service accounts

### Acceptance Criteria

- SSO login works with at least 2 providers
- Viewer role cannot access admin or data source settings
- ABAC restricts row-level data correctly per user attribute

## [Feature 107135](https://dev.azure.com/erainfotechbd/ERA%20InfoTech%20Limited/_workitems/edit/107135): M11 — API Specifications, SDK & Widgets

### Overview

Provide a public-facing API, developer SDK, and embeddable widgets to allow third-party integrations and custom deployments of InsightX capabilities.

### Scope

- RESTful API with OpenAPI 3.0 specification
- GraphQL API for flexible querying
- Developer SDK (JavaScript/TypeScript, Python)
- Embeddable insight widgets (React component, iframe)
- API authentication (API keys, OAuth tokens)
- Interactive API documentation (Swagger UI / Redoc)
- Rate limiting and usage quota management
- Webhook support for event subscriptions
- Sandbox/test environment for API consumers

### Acceptance Criteria

- All platform features accessible via REST API
- SDK works in Node.js and Python environments
- Embedded widget renders correctly in external apps
