-- database/migrations/001_create_datasources.sql
-- Run this against your InsightX metadata database (PostgreSQL recommended).

CREATE TABLE datasources (
    -- UUID primary key: avoids sequential ID enumeration
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Human-readable name, unique per tenant
    name                  VARCHAR(100)  NOT NULL,
    tenant_id             VARCHAR(100)  NOT NULL,

    -- One of: 'postgresql', 'mssql', 'oracle'
    engine                VARCHAR(20)   NOT NULL,

    -- Connection details (host/port/db stored in plaintext — not sensitive)
    host                  VARCHAR(255)  NOT NULL,
    port                  INTEGER       NOT NULL,
    database_name         VARCHAR(255)  NOT NULL,

    -- Oracle-specific: 'sid' or 'service_name'; NULL for other engines
    oracle_connection_type VARCHAR(20)  CHECK (oracle_connection_type IN ('sid', 'service_name')),

    -- Auth: method label stored for display; actual credentials are encrypted
    auth_method           VARCHAR(20)   NOT NULL,
    encrypted_credentials TEXT          NOT NULL,  -- AES-256-GCM: "iv:authTag:ciphertext"

    -- TLS: cert content is NOT stored in DB; only server-side file paths are referenced
    tls_enabled           BOOLEAN       NOT NULL DEFAULT FALSE,
    tls_verify_server_cert BOOLEAN      NOT NULL DEFAULT TRUE,
    tls_mode              VARCHAR(20),             -- 'require', 'verify-full', 'encrypt', etc.
    tls_ca_cert_path      VARCHAR(500),            -- Server-side path to CA cert file
    tls_client_cert_path  VARCHAR(500),            -- Server-side path to client cert
    tls_client_key_path   VARCHAR(500),            -- Server-side path to client key

    -- Metadata
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by            VARCHAR(100),
    last_tested_at        TIMESTAMPTZ,
    last_test_status      VARCHAR(20)   CHECK (last_test_status IN ('success', 'failed')),

    -- Enforce uniqueness: two sources in same tenant cannot share a name
    CONSTRAINT uq_datasource_name_per_tenant UNIQUE (tenant_id, name)
);

-- Fast lookup by tenant (almost every query will filter by this)
CREATE INDEX idx_datasources_tenant ON datasources (tenant_id);