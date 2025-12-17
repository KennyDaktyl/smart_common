from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


class Installation(Base):
    """
    Represents a logical user installation (home, business, or physical location).
    """

    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    station_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    station_addr: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Owner ---
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="installations",
    )

    # --- Relations ---
    microcontrollers: Mapped[list["Microcontroller"]] = relationship(
        "Microcontroller",
        back_populates="installation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Installation id={self.id} "
            f"name={self.name} "
            f"station_code={self.station_code} "
            f"user_id={self.user_id}>"
        )
