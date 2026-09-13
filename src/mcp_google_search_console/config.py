"""Explicit, immutable process configuration; no dotenv or automatic credential discovery."""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import GSCError
from .models import SiteURL

READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
WRITE_SCOPE = "https://www.googleapis.com/auth/webmasters"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    credentials_file: Path | None = Field(default=None, repr=False)
    enable_sitemap_writes: bool = Field(default=False, strict=True)
    allowed_sites: frozenset[SiteURL] | None = None
    request_timeout_seconds: float = Field(default=30, ge=1, le=120, allow_inf_nan=False)
    max_retries: int = Field(default=2, ge=0, le=5, strict=True)
    max_response_bytes: int = Field(default=16 * 1024 * 1024, ge=1024, strict=True)

    @property
    def scope(self) -> str:
        return WRITE_SCOPE if self.enable_sitemap_writes else READONLY_SCOPE

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        try:
            writes = env.get("GSC_ENABLE_SITEMAP_WRITES", "false").lower()
            if writes not in {"true", "false"}:
                raise ValueError("Invalid boolean")
            allowed = None
            if "GSC_ALLOWED_SITES" in env:
                entries = json.loads(env["GSC_ALLOWED_SITES"])
                if not isinstance(entries, list) or not all(isinstance(s, str) for s in entries):
                    raise ValueError("Invalid allowlist")
                allowed = frozenset(entries)
            return cls(
                credentials_file=Path(env["GOOGLE_APPLICATION_CREDENTIALS"])
                if env.get("GOOGLE_APPLICATION_CREDENTIALS")
                else None,
                enable_sitemap_writes=writes == "true",
                allowed_sites=allowed,
                request_timeout_seconds=float(env.get("GSC_REQUEST_TIMEOUT_SECONDS", "30")),
                max_retries=int(env.get("GSC_MAX_RETRIES", "2")),
                max_response_bytes=int(env.get("GSC_MAX_RESPONSE_BYTES", str(16 * 1024 * 1024))),
            )
        except (ValueError, TypeError, ValidationError):
            raise GSCError(
                "configuration_error",
                "Invalid GSC configuration; check the README environment table.",
            ) from None
