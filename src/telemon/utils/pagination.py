"""Pagination utilities."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginationResult(Generic[T]):
    """Result of a paginated query."""

    items: list[T]
    page: int
    per_page: int
    total_items: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


class Paginator(Generic[T]):
    """Helper class for pagination."""

    def __init__(self, items: list[T], per_page: int = 10):
        """Initialize paginator.

        Args:
            items: List of all items
            per_page: Items per page
        """
        self.items = items
        self.per_page = per_page
        self.total_items = len(items)
        self.total_pages = max(1, (self.total_items + per_page - 1) // per_page)

    def get_page(self, page: int) -> PaginationResult[T]:
        """Get a specific page of results.

        Args:
            page: Page number (1-indexed)

        Returns:
            PaginationResult with the page items and metadata
        """
        # Clamp page to valid range
        page = max(1, min(page, self.total_pages))

        start = (page - 1) * self.per_page
        end = start + self.per_page

        return PaginationResult(
            items=self.items[start:end],
            page=page,
            per_page=self.per_page,
            total_items=self.total_items,
            total_pages=self.total_pages,
        )


def paginate_list(items: list[T], page: int, per_page: int = 10) -> PaginationResult[T]:
    """Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        PaginationResult with the page items and metadata
    """
    return Paginator(items, per_page).get_page(page)
