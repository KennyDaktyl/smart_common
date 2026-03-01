from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from smart_common.core.db import Base
from smart_common.enums.scheduler import SchedulerCommandAction, SchedulerCommandStatus


class SchedulerCommand(Base):
    __tablename__ = "scheduler_commands"

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "slot_id",
            "minute_key",
            "action",
            name="uq_scheduler_idempotency",
        ),
        Index(
            "idx_scheduler_commands_pending",
            "status",
            "next_retry_at",
            "minute_key",
        ),
        Index(
            "idx_scheduler_commands_mc",
            "microcontroller_uuid",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    command_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )
    minute_key: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    device_number: Mapped[int] = mapped_column(Integer, nullable=False)
    microcontroller_uuid: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    scheduler_id: Mapped[int] = mapped_column(
        ForeignKey("schedulers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("scheduler_slots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action: Mapped[SchedulerCommandAction] = mapped_column(
        Enum(SchedulerCommandAction, name="scheduler_command_action_enum"),
        nullable=False,
    )
    status: Mapped[SchedulerCommandStatus] = mapped_column(
        Enum(SchedulerCommandStatus, name="scheduler_command_status_enum"),
        nullable=False,
        default=SchedulerCommandStatus.PENDING,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ack_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trigger_reason: Mapped[str | None] = mapped_column(String)
    measured_value: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    measured_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
