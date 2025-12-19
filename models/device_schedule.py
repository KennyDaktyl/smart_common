from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base


class DeviceSchedule(Base):
    """
    Time window that controls when a Device can run in either AUTO or MANUAL mode.
    Multiple schedules can coexist for a single Device (e.g., different weekdays).
    """

    __tablename__ = "device_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 0 = Monday, 6 = Sunday (per datetime.weekday())
    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="0=Mon, 6=Sun",
    )

    start_time: Mapped[str] = mapped_column(
        nullable=False,
        comment="HH:MM",
    )

    end_time: Mapped[str] = mapped_column(
        nullable=False,
        comment="HH:MM",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    device = relationship(
        "Device",
        back_populates="schedules",
    )

    def __repr__(self) -> str:
        return (
            f"<DeviceSchedule device_id={self.device_id} "
            f"dow={self.day_of_week} "
            f"{self.start_time}-{self.end_time}>"
        )
