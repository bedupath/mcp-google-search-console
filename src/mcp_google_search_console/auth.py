"""Lazy service-account authentication using Google's signing and refresh implementation."""

import asyncio
import json
import time
from typing import Any, Protocol

import httpx
from google.auth.exceptions import TransportError
from google.oauth2 import service_account

from .config import Settings
from .errors import GSCError

TOKEN_URL = "https://oauth2.googleapis.com/token"


class TokenProvider(Protocol):
    async def get_token(self) -> str: ...


class _TokenResponse:
    def __init__(self, response: httpx.Response, data: bytes) -> None:
        self.status = response.status_code
        self.headers = response.headers
        self.data = data


class _RefreshRequest:
    """Google-auth transport with a fixed endpoint and bounded retry/response budget."""

    def __init__(self, timeout: float) -> None:
        self.deadline = time.monotonic() + timeout
        self.calls = 0

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _TokenResponse:
        self.calls += 1
        remaining = self.deadline - time.monotonic()
        if url != TOKEN_URL or method != "POST" or self.calls > 3 or remaining <= 0:
            raise TransportError("Token request rejected or refresh budget exceeded")
        try:
            with httpx.Client(timeout=remaining, follow_redirects=False, trust_env=False) as client:
                with client.stream(method, url, content=body, headers=headers) as response:
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 256 * 1024 or time.monotonic() > self.deadline:
                            raise TransportError("Token response exceeded refresh budget")
                    return _TokenResponse(response, bytes(data))
        except httpx.HTTPError:
            raise TransportError("Token endpoint transport failure") from None


class ServiceAccountAuth:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._credentials: Any = None
        self._lock = asyncio.Lock()

    def _load_and_refresh(self) -> str:
        if self._credentials is None:
            path = self._settings.credentials_file
            if path is None:
                raise GSCError(
                    "credentials_missing",
                    "Set GOOGLE_APPLICATION_CREDENTIALS to a service-account file.",
                )
            try:
                if not path.is_absolute():
                    raise ValueError("Expected absolute credential path")
                with path.open(encoding="utf-8") as source:
                    info = json.load(source)
                if (
                    not isinstance(info, dict)
                    or info.get("type") != "service_account"
                    or info.get("token_uri") != TOKEN_URL
                    or info.get("universe_domain", "googleapis.com") != "googleapis.com"
                ):
                    raise ValueError("Unsupported credential configuration")
                self._credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=[self._settings.scope]
                )
            except Exception:
                raise GSCError(
                    "credentials_invalid",
                    "Cannot load service-account credentials; check the file and Google token URI.",
                ) from None
        try:
            if not self._credentials.valid:
                self._credentials.refresh(_RefreshRequest(self._settings.request_timeout_seconds))
            token = self._credentials.token
            if not isinstance(token, str) or not token:
                raise ValueError("Missing access token")
            return token
        except Exception:
            raise GSCError(
                "authentication_failed", "Google service-account token refresh failed."
            ) from None

    async def get_token(self) -> str:
        async with self._lock:
            # Keep the refresh lock until the worker exits even if the caller is cancelled.
            task = asyncio.create_task(asyncio.to_thread(self._load_and_refresh))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                try:
                    await task
                except Exception:
                    pass
                raise
