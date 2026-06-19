from __future__ import annotations

import uuid
from datetime import datetime

from enum import Enum as PyEnum

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


SCHEMA_FAMILYMANAGER = "ATPTLP_familymanager"
SCHEMA_OPENMODELS = "ATPTLP_openmodels"
SCHEMA_INFO = "atptlp_info"
SCHEMA_STG_BIM = "stg_bim"


class FamilyStatus(str, PyEnum):
    INITIATED = "initiated"
    UPLOADED = "uploaded"
    PARSED = "parsed"
    READY = "ready"
    FAILED = "failed"


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[FamilyStatus] = mapped_column(
        SAEnum(FamilyStatus, native_enum=False), nullable=False, default=FamilyStatus.INITIATED
    )
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    family_name: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool | None] = mapped_column(Boolean)
    parent_family_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    etag: Mapped[str | None] = mapped_column(String(128))
    has_thumbnail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_families_project_id", "project_id"),
        Index("ix_families_sha256", "sha256"),
        Index("ix_families_identity", "project_id", "family_name", "category", "is_primary"),
        {"schema": SCHEMA_FAMILYMANAGER},
    )

    parameters: Mapped[list["FamilyParameter"]] = relationship(
        back_populates="family", cascade="all, delete-orphan", passive_deletes=True
    )
    type_values: Mapped[list["FamilyTypeValue"]] = relationship(
        back_populates="family", cascade="all, delete-orphan", passive_deletes=True
    )


class FamilyParameter(Base):
    __tablename__ = "family_parameters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA_FAMILYMANAGER}.families.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column("param_name", String(255), nullable=False)
    is_instance: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_guid: Mapped[str | None] = mapped_column(String(64))
    storage_type: Mapped[str | None] = mapped_column(String(64))
    spec: Mapped[str | None] = mapped_column(Text)

    family: Mapped[Family] = relationship(back_populates="parameters")

    __table_args__ = (
        UniqueConstraint("family_id", "param_name", name="uq_family_param_name"),
        Index("ix_family_parameters_family_id", "family_id"),
        {"schema": SCHEMA_FAMILYMANAGER},
    )


class FamilyTypeValue(Base):
    __tablename__ = "family_type_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA_FAMILYMANAGER}.families.id", ondelete="CASCADE")
    )
    type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    param_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text)

    family: Mapped[Family] = relationship(back_populates="type_values")

    __table_args__ = (
        UniqueConstraint("family_id", "type_name", "param_name", name="uq_family_type_param"),
        Index("ix_family_type_values_family_id", "family_id"),
        {"schema": SCHEMA_FAMILYMANAGER},
    )


class OpeningStatus(str, PyEnum):
    NEW = "new"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"


class OpeningHistoryEventType(str, PyEnum):
    CREATED = "created"
    UPDATED = "updated"
    SOFT_DELETED = "softDeleted"
    STATUS_CHANGED = "statusChanged"


class Opening(Base):
    __tablename__ = "openings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    element_unique_id: Mapped[str] = mapped_column(Text, nullable=False)
    element_id: Mapped[int | None] = mapped_column(BigInteger)
    family_name: Mapped[str | None] = mapped_column(Text)
    type_name: Mapped[str | None] = mapped_column(Text)
    category_name: Mapped[str | None] = mapped_column(Text)
    level_name: Mapped[str | None] = mapped_column(Text)
    location_x: Mapped[float | None] = mapped_column(Float)
    location_y: Mapped[float | None] = mapped_column(Float)
    location_z: Mapped[float | None] = mapped_column(Float)
    width: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    depth: Mapped[float | None] = mapped_column(Float)
    diameter: Mapped[float | None] = mapped_column(Float)
    extra_fields: Mapped[dict | None] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OpeningStatus] = mapped_column(
        SAEnum(OpeningStatus, native_enum=False), nullable=False, default=OpeningStatus.NEW
    )
    schedule_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["OpeningHistory"]] = relationship(
        back_populates="opening", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("model_guid", "element_unique_id", name="uq_openings_model_element"),
        Index("ix_openings_model_guid", "model_guid"),
        {"schema": SCHEMA_OPENMODELS},
    )


class OpeningHistory(Base):
    __tablename__ = "opening_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    opening_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA_OPENMODELS}.openings.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[OpeningHistoryEventType] = mapped_column(SAEnum(OpeningHistoryEventType, native_enum=False), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(Text)

    opening: Mapped[Opening] = relationship(back_populates="history")

    __table_args__ = (Index("ix_opening_history_opening_id", "opening_id"), {"schema": SCHEMA_OPENMODELS})


class BimdataSnapshotStatus(str, PyEnum):
    CREATED = "created"
    COMPLETED = "completed"
    FAILED = "failed"


class BimdataSnapshot(Base):
    __tablename__ = "model_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_windows_user: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    revit_version: Mapped[int] = mapped_column(Integer, nullable=False)
    pbp_x: Mapped[float | None] = mapped_column(Float)
    pbp_y: Mapped[float | None] = mapped_column(Float)
    pbp_z: Mapped[float | None] = mapped_column(Float)
    pbp_angle: Mapped[float | None] = mapped_column(Float)
    sp_x: Mapped[float | None] = mapped_column(Float)
    sp_y: Mapped[float | None] = mapped_column(Float)
    sp_z: Mapped[float | None] = mapped_column(Float)
    fop_name: Mapped[str | None] = mapped_column(Text)
    fop_path: Mapped[str | None] = mapped_column(Text)
    project_number: Mapped[str | None] = mapped_column(Text)
    project_name: Mapped[str | None] = mapped_column(Text)
    project_stage: Mapped[str | None] = mapped_column(Text)
    worksets_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_files_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[BimdataSnapshotStatus] = mapped_column(
        SAEnum(BimdataSnapshotStatus, native_enum=False),
        nullable=False,
        default=BimdataSnapshotStatus.CREATED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    elements: Mapped[list["BimdataElement"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_model_snapshots_company_date", "company_id", "snapshot_date"),
        {"schema": SCHEMA_STG_BIM},
    )


class BimdataElement(Base):
    __tablename__ = "mep_elements"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_STG_BIM}.model_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    element_guid: Mapped[str] = mapped_column(Text, primary_key=True)
    revit_id: Mapped[int | None] = mapped_column(Integer)
    category_name: Mapped[str | None] = mapped_column(Text)
    family_name: Mapped[str | None] = mapped_column(Text)
    type_name: Mapped[str | None] = mapped_column(Text)
    workset_name: Mapped[str | None] = mapped_column(Text)
    level_guid: Mapped[str | None] = mapped_column(Text)
    level_name: Mapped[str | None] = mapped_column(Text)
    space_guid: Mapped[str | None] = mapped_column(Text)
    system_classification: Mapped[str | None] = mapped_column(Text)
    system_name: Mapped[str | None] = mapped_column(Text)
    is_linear: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    length: Mapped[float | None] = mapped_column(Float)
    dimension_1: Mapped[float | None] = mapped_column(Float)
    dimension_2: Mapped[float | None] = mapped_column(Float)
    location_point: Mapped[dict | None] = mapped_column(JSONB)
    bounding_box_volume: Mapped[float | None] = mapped_column(Float)
    bep_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    connectors_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    snapshot: Mapped[BimdataSnapshot] = relationship(back_populates="elements")

    __table_args__ = ({"schema": SCHEMA_STG_BIM},)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": SCHEMA_INFO}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users: Mapped[list["CompanyUser"]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )


class CompanyUser(Base):
    __tablename__ = "company_users"
    __table_args__ = {"schema": SCHEMA_INFO}

    company_id: Mapped[str] = mapped_column(
        Text, ForeignKey(f"{SCHEMA_INFO}.companies.company_id", ondelete="CASCADE"), primary_key=True
    )
    windows_user: Mapped[str] = mapped_column(Text, primary_key=True)

    company: Mapped[Company] = relationship(back_populates="users")


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    company_id: Mapped[str] = mapped_column(Text, primary_key=True)
    windows_user: Mapped[str] = mapped_column(Text, primary_key=True)
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_FAMILYMANAGER}.families.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_user_favorites_lookup", "company_id", "windows_user"),
        {"schema": SCHEMA_FAMILYMANAGER},
    )


class UserProject(Base):
    __tablename__ = "user_projects"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    __table_args__ = (
        Index("ix_user_projects_user_id", "user_id"),
        Index("ix_user_projects_project_id", "project_id"),
        {"schema": SCHEMA_FAMILYMANAGER},
    )

