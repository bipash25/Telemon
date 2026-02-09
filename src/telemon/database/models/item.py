"""Item model for shop and inventory."""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base, TimestampMixin


class Item(Base):
    """Static data for items."""

    __tablename__ = "items"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name_lower: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Category
    category: Mapped[str] = mapped_column(String(30), nullable=False)  # evolution, battle, utility, etc.

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Shop info
    cost: Mapped[int] = mapped_column(Integer, default=0)  # 0 = not purchasable
    sell_price: Mapped[int] = mapped_column(Integer, default=0)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Item properties
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_holdable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Effect data (JSON for flexibility)
    effect: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Sprite
    sprite_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Item {self.id} {self.name}>"


class InventoryItem(Base, TimestampMixin):
    """User's inventory item."""

    __tablename__ = "inventory_items"

    # Composite primary key
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.id"),
        primary_key=True,
    )

    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    user = relationship("User", back_populates="inventory_items")
    item = relationship("Item", lazy="joined")

    def __repr__(self) -> str:
        return f"<InventoryItem user={self.user_id} item={self.item_id} qty={self.quantity}>"
