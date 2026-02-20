from __future__ import annotations

import uuid
from datetime import datetime

from enum import Enum as PyEnum

from sqlalchemy import UUID, Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint, func, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


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
    status: Mapped[FamilyStatus] = mapped_column(
        SAEnum(FamilyStatus, native_enum=False), nullable=False, default=FamilyStatus.INITIATED
    )
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    etag: Mapped[str | None] = mapped_column(String(128))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_families_project_id", "project_id"),
        Index("ix_families_sha256", "sha256"),
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
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"))
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
    )


class FamilyTypeValue(Base):
    __tablename__ = "family_type_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"))
    type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    param_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text)

    family: Mapped[Family] = relationship(back_populates="type_values")

    __table_args__ = (
        UniqueConstraint("family_id", "type_name", "param_name", name="uq_family_type_param"),
        Index("ix_family_type_values_family_id", "family_id"),
    )


class UserProject(Base):
    __tablename__ = "user_projects"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    __table_args__ = (
        Index("ix_user_projects_user_id", "user_id"),
        Index("ix_user_projects_project_id", "project_id"),
    )

