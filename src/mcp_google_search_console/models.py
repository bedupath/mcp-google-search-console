"""Validated API inputs. Provider responses intentionally have no lossy response model."""

import re
from datetime import date
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


def validate_http_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme in {"http", "https"}
            and parts.hostname
            and parts.username is None
            and parts.password is None
            and not parts.fragment
            and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
            and "\\" not in value
        )
        _ = parts.port
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Expected an absolute HTTP(S) URL without credentials or fragment")
    return value


def validate_site_url(value: str) -> str:
    if value.startswith("sc-domain:"):
        domain = value.removeprefix("sc-domain:")
        if (
            not domain
            or len(domain) > 253
            or any(
                not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in domain.split(".")
            )
        ):
            raise ValueError("Expected sc-domain: followed by a domain (use punycode for IDNs)")
        return value
    validate_http_url(value)
    if urlsplit(value).query:
        raise ValueError("A URL-prefix property cannot contain a query string")
    return value


def validate_date(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Expected a date in YYYY-MM-DD format")
    date.fromisoformat(value)
    return value


SiteURL = Annotated[str, Field(strict=True), AfterValidator(validate_site_url)]
HTTPURL = Annotated[str, Field(strict=True), AfterValidator(validate_http_url)]
DateString = Annotated[str, Field(strict=True), AfterValidator(validate_date)]
FilterDimension = Literal["country", "device", "page", "query", "searchAppearance"]
Dimension = Literal["country", "device", "page", "query", "searchAppearance", "date", "hour"]


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class DimensionFilter(APIModel):
    dimension: FilterDimension
    expression: Annotated[str, Field(strict=True, max_length=4096)]
    operator: Literal[
        "equals", "notEquals", "contains", "notContains", "includingRegex", "excludingRegex"
    ] = "equals"


class DimensionFilterGroup(APIModel):
    group_type: Literal["and"] = "and"
    filters: list[DimensionFilter] = Field(default_factory=list)


class SearchAnalyticsQuery(APIModel):
    """One Google query page; defaults match Google, not a reporting strategy."""

    start_date: DateString = Field(description="Inclusive date in America/Los_Angeles")
    end_date: DateString = Field(description="Inclusive date in America/Los_Angeles")
    dimensions: list[Dimension] | None = None
    type: Literal["web", "image", "video", "news", "discover", "googleNews"] | None = None
    dimension_filter_groups: list[DimensionFilterGroup] | None = None
    aggregation_type: Literal["auto", "byPage", "byProperty", "byNewsShowcasePanel"] | None = None
    data_state: Literal["final", "all", "hourly_all"] | None = None
    row_limit: Annotated[int, Field(strict=True, ge=1, le=25000)] | None = None
    start_row: Annotated[int, Field(strict=True, ge=0)] | None = None

    @model_validator(mode="after")
    def validate_query(self) -> Self:
        if self.start_date > self.end_date:
            raise ValueError("startDate must be on or before endDate")
        dimensions = self.dimensions or []
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("Grouping dimensions must be unique")
        filters = [f for group in self.dimension_filter_groups or [] for f in group.filters]
        has_page = "page" in dimensions or any(f.dimension == "page" for f in filters)
        if self.aggregation_type == "byProperty" and (
            has_page or self.type in {"discover", "googleNews"}
        ):
            raise ValueError("byProperty cannot be used with page, discover, or googleNews")
        return self
