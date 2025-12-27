from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.core.db import Base


class MicrocontrollerSensorCapability(Base):
    __tablename__ = "microcontroller_sensor_capabilities"
    __table_args__ = (
        UniqueConstraint(
            "microcontroller_id",
            "sensor_type",
            name="uq_microcontroller_sensor_capability",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    microcontroller_id: Mapped[int] = mapped_column(
        ForeignKey("microcontrollers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Persist sensor identifiers as plain strings to keep the schema stable.
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)

    microcontroller = relationship(
        "Microcontroller",
        back_populates="sensor_capabilities",
    )

    def __repr__(self) -> str:
        return (
            "<MicrocontrollerSensorCapability "
            f"microcontroller_id={self.microcontroller_id} "
            f"sensor_type={self.sensor_type}>"
        )
