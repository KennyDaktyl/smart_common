from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Boolean,
)
from sqlalchemy.orm import relationship

from smart_common.core.db import Base
from smart_common.enums.provider import (
    ProviderType,
    PowerUnit,
    ProviderKind,
    ProviderVendor,
)


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    uuid = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        default=uuid4,
    )
    installation_id = Column(
        Integer,
        ForeignKey("installations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    provider_type = Column(
        Enum(ProviderType, name="provider_type_enum"),
        nullable=False,
    )
    kind = Column(
        Enum(ProviderKind, name="provider_kind_enum"),
        nullable=False,
    )
    vendor = Column(Enum(ProviderVendor), nullable=True)
    model = Column(String, nullable=True)
    unit = Column(
        Enum(PowerUnit, name="power_unit_enum"),
        nullable=False,
    )
    min_value = Column(Numeric(12, 4), nullable=False)
    max_value = Column(Numeric(12, 4), nullable=False)
    last_value = Column(Numeric(12, 4), nullable=True)
    last_measurement_at = Column(DateTime(timezone=True), nullable=True)
    polling_interval_sec = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    installation = relationship(
        "Installation",
        back_populates="providers",
    )
    raspberries = relationship("Raspberry", back_populates="provider", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Provider id={self.id} "
            f"kind={self.kind} "
            f"type={self.provider_type} "
            f"vendor={self.vendor} "
            f"unit={self.unit}>"
        )
