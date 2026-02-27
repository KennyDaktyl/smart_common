from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String
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

    scheduler = relationship("Scheduler", back_populates="slots")
