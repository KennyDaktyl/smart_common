from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base


class Scheduler(Base):
    __tablename__ = "schedulers"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="schedulers")
    slots = relationship(
        "SchedulerSlot",
        back_populates="scheduler",
        cascade="all, delete-orphan",
        order_by="SchedulerSlot.id",
    )
    devices = relationship("Device", back_populates="scheduler")
