"""Shared schemas: generic paginated response and pagination query params."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Paginated list response: {items, total, page, page_size}."""

    items: list[T]
    total: int
    page: int
    page_size: int


class PaginationParams:
    """Query-param dependency: `params: PaginationParams = Depends()`."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Number of rows to skip for the current page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Maximum number of rows to return."""
        return self.page_size
