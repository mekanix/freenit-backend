from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    total: int = Field(0, description="Total number of items in DB")
    page: int = Field(0, description="Current page")
    pages: int = Field(0, description="Total number of pages")
    perpage: int = Field(10, description="Items per page")
    data: list[T] = Field(..., description="List of results for the current page")


async def paginate(query, page: int, perpage: int) -> Page:
    total = await query.count()
    pages = ceil(total / perpage) if perpage else 0
    if total > 0 and page > pages:
        raise ValueError("No such page")
    offset = max(page - 1, 0) * perpage
    data = await query.offset(offset).limit(perpage).all()
    return Page(data=data, page=page, perpage=perpage, pages=pages, total=total)
