from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_common.enums.user import UserRole
from smart_common.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)

    installations: Mapped[list["Installation"]] = relationship(
        "Installation", back_populates="user", cascade="all, delete-orphan"
    )
    raspberries: Mapped[list["Raspberry"]] = relationship(
        "Raspberry", back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="user", cascade="all, delete-orphan"
    )
