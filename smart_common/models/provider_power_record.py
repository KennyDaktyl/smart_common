from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric

from smart_common.core.db import Base


class ProviderPowerRecord(Base):

    __tablename__ = "provider_power_records"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    current_power = Column(Numeric(10, 2), nullable=True)
    timestamp = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f"<ProviderPowerRecord(provider_id={self.provider_id}, current_power={self.current_power}, timestamp={self.timestamp})>"
