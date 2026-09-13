"""Reusable async client. No MCP dependency, reporting logic, or implicit pagination."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, Self, cast
from urllib.parse import quote

import httpx
from pydantic import TypeAdapter, ValidationError

from .auth import ServiceAccountAuth, TokenProvider
from .config import Settings
from .errors import GSCError
from .models import HTTPURL, SearchAnalyticsQuery, SiteURL

API_ROOT = "https://www.googleapis.com/webmasters/v3"
INSPECTION_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
_SITE = TypeAdapter(SiteURL)
_URL = TypeAdapter(HTTPURL)
_RETRY_STATUS = {429, 500, 502, 503, 504}
_QUOTA_REASONS = {
    "rateLimitExceeded",
    "userRateLimitExceeded",
    "quotaExceeded",
    "dailyLimitExceeded",
}


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON number")


class GSCClient:
    def __init__(
        self,
        settings: Settings,
        *,
        auth: TokenProvider | None = None,
        http_client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings
        self._auth = auth if auth is not None else ServiceAccountAuth(settings)
        self._owns_http = http_client is None
        self._http = (
            http_client
            if http_client is not None
            else httpx.AsyncClient(
                timeout=settings.request_timeout_seconds, follow_redirects=False, trust_env=False
            )
        )
        self._sleep = sleep

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _site_path(self, site_url: str) -> str:
        try:
            _SITE.validate_python(site_url)
        except ValidationError:
            raise GSCError("invalid_input", "Invalid site_url property identifier.") from None
        if self.settings.allowed_sites is not None and site_url not in self.settings.allowed_sites:
            raise GSCError(
                "property_not_allowed", "The exact site_url is not in GSC_ALLOWED_SITES."
            )
        return f"{API_ROOT}/sites/{quote(site_url, safe='')}"

    @staticmethod
    def _validate_url(url: str) -> None:
        try:
            _URL.validate_python(url)
        except ValidationError:
            raise GSCError("invalid_input", "Expected an absolute HTTP(S) URL.") from None

    def _require_writes(self) -> None:
        if not self.settings.enable_sitemap_writes:
            raise GSCError("writes_disabled", "Sitemap writes are disabled in this process.")

    @staticmethod
    def _http_error(status: int, body: bytes, *, write: bool) -> GSCError:
        quota = status == 429
        if status == 403:
            try:
                data = json.loads(body)
                quota = any(
                    entry.get("reason") in _QUOTA_REASONS
                    for entry in data["error"].get("errors", [])
                    if isinstance(entry, dict)
                )
            except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
                pass
        if quota:
            code, message = (
                "quota_exceeded",
                "Google rejected the request because of a quota limit.",
            )
        elif status == 401:
            code, message = "unauthorized", "Google rejected the access token."
        elif status == 403:
            code, message = (
                "permission_denied",
                "Google denied access; check property access and API enablement.",
            )
        elif status == 404:
            code, message = "not_found", "Google did not find the requested resource."
        elif status == 400:
            code, message = (
                "invalid_request",
                "Google rejected the request; check API parameter compatibility.",
            )
        else:
            code, message = "google_api_error", "Google returned an unsuccessful HTTP response."
        return GSCError(
            code,
            message,
            http_status=status,
            retryable=not write and (quota or status in _RETRY_STATUS),
            outcome_unknown=write and (status >= 500 or status == 408),
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        # Defense in depth: even internal callers cannot bypass write configuration.
        if write or method in {"PUT", "DELETE", "PATCH"}:
            self._require_writes()
        token = await self._auth.get_token()
        attempts = 1 if write else self.settings.max_retries + 1
        for attempt in range(attempts):
            retry_after = 0.0
            try:
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    async with self._http.stream(
                        method,
                        url,
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                        json=body,
                        params=params,
                        follow_redirects=False,
                        timeout=self.settings.request_timeout_seconds,
                    ) as response:
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > self.settings.max_response_bytes:
                                raise GSCError(
                                    "response_too_large",
                                    "Response exceeds GSC_MAX_RESPONSE_BYTES; "
                                    "no partial data returned.",
                                    outcome_unknown=write,
                                )
                        if not response.is_success:
                            error = self._http_error(response.status_code, bytes(data), write=write)
                            try:
                                retry_after = min(
                                    30.0, max(0.0, float(response.headers.get("Retry-After", "0")))
                                )
                            except ValueError:
                                pass
                            raise error
                        if not data and write:
                            return {}
                        try:
                            result = json.loads(data, parse_constant=_reject_constant)
                            if not isinstance(result, dict):
                                raise ValueError("Expected an object")
                        except (ValueError, UnicodeDecodeError, RecursionError):
                            raise GSCError(
                                "invalid_response",
                                "Google returned an invalid JSON object.",
                                outcome_unknown=write,
                            ) from None
                        return cast(dict[str, Any], result)
            except (httpx.HTTPError, TimeoutError):
                error = GSCError(
                    "transport_error",
                    "Google request failed or timed out.",
                    retryable=not write,
                    outcome_unknown=write,
                )
            except GSCError as exc:
                error = exc
            if not error.retryable or attempt == attempts - 1:
                raise error from None
            await self._sleep(max(retry_after, min(2.0**attempt, 8.0)))
        raise AssertionError("Unreachable")

    async def list_sites(self) -> dict[str, Any]:
        """Return Google's site list, restricted to allowed_sites when configured."""
        if self.settings.allowed_sites == frozenset():
            return {"siteEntry": []}
        result = await self._request("GET", f"{API_ROOT}/sites")
        if self.settings.allowed_sites is not None and "siteEntry" in result:
            entries = result["siteEntry"]
            if not isinstance(entries, list) or not all(
                isinstance(e, dict) and isinstance(e.get("siteUrl"), str) for e in entries
            ):
                raise GSCError("invalid_response", "Google returned an invalid site list.")
            result = {
                **result,
                "siteEntry": [
                    e for e in entries if e.get("siteUrl") in self.settings.allowed_sites
                ],
            }
        return result

    async def get_site(self, site_url: str) -> dict[str, Any]:
        return await self._request("GET", self._site_path(site_url))

    async def query_search_analytics(
        self, site_url: str, query: SearchAnalyticsQuery
    ) -> dict[str, Any]:
        url = f"{self._site_path(site_url)}/searchAnalytics/query"
        try:
            validated = SearchAnalyticsQuery.model_validate(query)
        except ValidationError:
            raise GSCError("invalid_input", "Invalid Search Analytics query.") from None
        return await self._request(
            "POST", url, body=validated.model_dump(by_alias=True, exclude_none=True)
        )

    async def inspect_url(
        self, site_url: str, inspection_url: str, language_code: str | None = None
    ) -> dict[str, Any]:
        self._site_path(site_url)
        self._validate_url(inspection_url)
        body = {"siteUrl": site_url, "inspectionUrl": inspection_url}
        if language_code is not None:
            if not isinstance(language_code, str) or not language_code or len(language_code) > 64:
                raise GSCError("invalid_input", "Invalid language_code.")
            body["languageCode"] = language_code
        return await self._request("POST", INSPECTION_URL, body=body)

    async def list_sitemaps(
        self, site_url: str, sitemap_index: str | None = None
    ) -> dict[str, Any]:
        url = f"{self._site_path(site_url)}/sitemaps"
        params = None
        if sitemap_index is not None:
            self._validate_url(sitemap_index)
            params = {"sitemapIndex": sitemap_index}
        return await self._request("GET", url, params=params)

    def _sitemap_path(self, site_url: str, feedpath: str) -> str:
        site = self._site_path(site_url)
        self._validate_url(feedpath)
        return f"{site}/sitemaps/{quote(feedpath, safe='')}"

    async def get_sitemap(self, site_url: str, feedpath: str) -> dict[str, Any]:
        return await self._request("GET", self._sitemap_path(site_url, feedpath))

    async def submit_sitemap(self, site_url: str, feedpath: str) -> dict[str, Any]:
        self._require_writes()
        return await self._request("PUT", self._sitemap_path(site_url, feedpath), write=True)

    async def delete_sitemap(self, site_url: str, feedpath: str) -> dict[str, Any]:
        self._require_writes()
        return await self._request("DELETE", self._sitemap_path(site_url, feedpath), write=True)
