from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import relationship

from smart_common.enums.device import DeviceMode
from smart_common.core.db import Base


class DeviceSchedule(Base):
    __tablename__ = "device_schedules"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    name = Column(String, nullable=True)
    day_of_week = Column(String, nullable=False)  # mon, tue, wed, ...
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    mode = Column(
        Enum(DeviceMode, name="device_mode", create_type=False),
        default=DeviceMode.AUTO_POWER,
        nullable=False,
    )
    threshold_kw = Column(Numeric(10, 3), nullable=True)
    enabled = Column(Boolean, default=True)

    device = relationship("Device", back_populates="schedules")

    def __repr__(self):
        return (
            f"<DeviceSchedule id={self.id} name={self.name!r} device={self.device_id} "
            f"{self.day_of_week} {self.start_time}-{self.end_time} "
            f"mode={self.mode} threshold={self.threshold_kw}>"
        )
