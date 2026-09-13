"""Errors safe to return over MCP: never include credentials or upstream bodies."""

from typing import Any


class GSCError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        retryable: bool = False,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retryable = retryable
        self.outcome_unknown = outcome_unknown

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "http_status": self.http_status,
            "retryable": self.retryable,
            "outcome_unknown": self.outcome_unknown,
        }
