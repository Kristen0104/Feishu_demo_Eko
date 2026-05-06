from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

PayloadT = TypeVar("PayloadT")


class ApiResponse(BaseModel, Generic[PayloadT]):
    code: int
    message: str
    data: PayloadT | None = None

    @classmethod
    def success(
        cls,
        data: PayloadT | None = None,
        *,
        message: str = "success",
    ) -> "ApiResponse[PayloadT]":
        return cls(code=0, message=message, data=data)
