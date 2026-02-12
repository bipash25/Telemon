"""Team / Guild model for player guilds."""

from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base, TimestampMixin


class Team(Base, TimestampMixin):
    """Represents a player team / guild."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tag", name="uq_teams_tag"),
        UniqueConstraint("name", name="uq_teams_name"),
    )

    # Auto-increment integer PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Display info
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    tag: Mapped[str] = mapped_column(String(5), nullable=False)  # 2-5 chars, uppercase
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Leader (Telegram user ID)
    leader_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Leveling
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(BigInteger, default=0)

    # Capacity — grows with level
    max_members: Mapped[int] = mapped_column(Integer, default=10)

    # Flexible settings (e.g. join_policy: "open" | "invite_only")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    members = relationship("User", back_populates="team", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Team [{self.tag}] {self.name} Lv{self.level}>"

    @property
    def display(self) -> str:
        """Format: [TAG] Name"""
        return f"[{self.tag}] {self.name}"
