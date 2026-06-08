# app/db/models/datasource.py
#
# PURPOSE:
#   SQLAlchemy ORM model for the datasources table.
#   Maps directly to the schema defined in database/migrations/001_create_datasources.sql.
#   Uses SQLAlchemy 2.0 Mapped/mapped_column syntax (type-annotated, IDE-friendly).
#
# SENSITIVE FIELDS — never returned via API:
#   encrypted_credentials:  AES-256-GCM ciphertext
#   tls_*_cert_path:        Server-side filesystem paths to cert files

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Datasource(Base):
    __tablename__ = "datasources"

    # Table-level constraints — mirror the SQL migration exactly
    __table_args__ = (
        # Two sources in the same tenant cannot share a name
        UniqueConstraint("tenant_id", "name", name="uq_datasource_name_per_tenant"),
        CheckConstraint(
            "oracle_connection_type IN ('sid', 'service_name')",
            name="chk_oracle_connection_type",
        ),
        CheckConstraint(
            "last_test_status IN ('success', 'failed')",
            name="chk_last_test_status",
        ),
        # Almost every query filters by tenant_id — index this
        Index("idx_datasources_tenant", "tenant_id"),
    )

    # --- Primary key ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key — avoids sequential ID enumeration",
    )

    # --- Identity ---
    name:      Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Engine ---
    # One of: 'postgresql', 'mssql', 'oracle'
    engine: Mapped[str] = mapped_column(String(20), nullable=False)

    # --- Connection details (not sensitive) ---
    host:          Mapped[str] = mapped_column(String(255), nullable=False)
    port:          Mapped[int] = mapped_column(Integer,     nullable=False)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Oracle-only: 'sid' or 'service_name'; NULL for PostgreSQL and MSSQL
    oracle_connection_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )

    # --- Authentication ---
    auth_method: Mapped[str] = mapped_column(String(20), nullable=False)

    # AES-256-GCM encrypted JSON string: "iv_hex:tag_hex:ciphertext_hex"
    # NEVER returned via the API — not even to the owning tenant
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)

    # --- TLS (paths are server-side references — not cert content) ---
    tls_enabled:            Mapped[bool]         = mapped_column(Boolean,     nullable=False, default=False)
    tls_verify_server_cert: Mapped[bool]         = mapped_column(Boolean,     nullable=False, default=True)
    tls_mode:               Mapped[Optional[str]] = mapped_column(String(20),  nullable=True)
    tls_ca_cert_path:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tls_client_cert_path:   Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tls_client_key_path:    Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Audit ---
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by:       Mapped[Optional[str]]      = mapped_column(String(100), nullable=True)
    last_tested_at:   Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_test_status: Mapped[Optional[str]]      = mapped_column(String(20),  nullable=True)