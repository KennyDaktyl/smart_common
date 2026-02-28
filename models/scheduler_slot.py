from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base
from smart_common.enums.scheduler import SchedulerDayOfWeek


class SchedulerSlot(Base):
    __tablename__ = "scheduler_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheduler_id: Mapped[int] = mapped_column(
        ForeignKey("schedulers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[SchedulerDayOfWeek] = mapped_column(
        Enum(SchedulerDayOfWeek, name="scheduler_day_of_week_enum"),
        nullable=False,
    )
    start_time: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        comment="HH:MM",
    )
    end_time: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        comment="HH:MM",
    )
    start_local_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM in user's local timezone",
    )
    end_local_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM in user's local timezone",
    )
    start_utc_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM normalized to UTC",
    )
    end_utc_time: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        comment="HH:MM normalized to UTC",
    )
    use_power_threshold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    power_threshold_value: Mapped[float | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Power threshold value for slot rule",
    )
    power_threshold_unit: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Power threshold unit (W, kW, MW)",
    )

    scheduler = relationship("Scheduler", back_populates="slots")
