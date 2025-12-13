from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.enums.device import DeviceMode
from smart_common.core.db import Base


class DeviceSchedule(Base):
    __tablename__ = "device_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    day_of_week: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    mode: Mapped[DeviceMode] = mapped_column(
        Enum(DeviceMode, name="device_mode", create_type=False),
        default=DeviceMode.AUTO_POWER,
        nullable=False,
    )
    threshold_kw: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    device = relationship("Device", back_populates="schedules")

    def __repr__(self):
        return (
            f"<DeviceSchedule id={self.id} name={self.name!r} device={self.device_id} "
            f"{self.day_of_week} {self.start_time}-{self.end_time} "
            f"mode={self.mode} threshold={self.threshold_kw}>"
        )
