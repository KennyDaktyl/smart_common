from __future__ import annotations

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship

from smart_common.core.db import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ---------------------------------
    # PERSONAL
    # ---------------------------------
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(32), nullable=True)

    # ---------------------------------
    # COMPANY (OPTIONAL)
    # ---------------------------------
    company_name = Column(String(255), nullable=True)
    company_vat = Column(String(64), nullable=True)
    company_address = Column(String(512), nullable=True)

    # ---------------------------------
    # META
    # ---------------------------------
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    # ---------------------------------
    # RELATIONS
    # ---------------------------------
    user = relationship(
        "User",
        back_populates="profile",
        lazy="joined",
    )
    def __repr__(self) -> str:
        return f"<UserProfile id={self.id} user_id={self.user_id}>"
