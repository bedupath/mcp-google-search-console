import pytest
from pydantic import TypeAdapter, ValidationError

from mcp_google_search_console.config import READONLY_SCOPE, WRITE_SCOPE, Settings
from mcp_google_search_console.errors import GSCError
from mcp_google_search_console.models import HTTPURL, SearchAnalyticsQuery, SiteURL


def test_config_default_scope_and_explicit_empty_allowlist():
    default = Settings.from_env({})
    assert default.scope == READONLY_SCOPE
    assert default.allowed_sites is None
    assert default.credentials_file is None
    assert Settings.from_env({"GSC_ALLOWED_SITES": "[]"}).allowed_sites == frozenset()
    assert Settings.from_env({"GSC_ENABLE_SITEMAP_WRITES": "true"}).scope == WRITE_SCOPE


@pytest.mark.parametrize(
    "key,value",
    [
        ("GSC_ENABLE_SITEMAP_WRITES", "yes"),
        ("GSC_ALLOWED_SITES", ""),
        ("GSC_ALLOWED_SITES", '"sc-domain:example.com"'),
        ("GSC_ALLOWED_SITES", "[123]"),
        ("GSC_ALLOWED_SITES", '["https://user:secret@example.com/"]'),
        ("GSC_REQUEST_TIMEOUT_SECONDS", "nan"),
        ("GSC_REQUEST_TIMEOUT_SECONDS", "inf"),
        ("GSC_REQUEST_TIMEOUT_SECONDS", "0"),
        ("GSC_MAX_RETRIES", "6"),
        ("GSC_MAX_RESPONSE_BYTES", "0"),
    ],
)
def test_bad_config_fails_closed_without_echoing_values(key, value):
    with pytest.raises(GSCError) as caught:
        Settings.from_env({key: value})
    assert caught.value.code == "configuration_error"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize(
    "site",
    [
        "sc-domain:example.com",
        "sc-domain:xn--bcher-kva.example",
        "https://example.com/",
        "http://example.com/blog/",
        "https://example.com:8443/",
    ],
)
def test_site_identifiers_preserved(site):
    assert TypeAdapter(SiteURL).validate_python(site) == site


@pytest.mark.parametrize(
    "site",
    [
        "example.com",
        "sc-domain:",
        "sc-domain:example.com/",
        "sc-domain:*.example.com",
        "https://user:secret@example.com/",
        "https://example.com/#fragment",
        "https://example.com/?q=a",
        "https://example.com\n/",
        "ftp://example.com/",
        "https://example.com:bad/",
        "https://example.com\\evil/",
        "sc-domain:-example.com",
    ],
)
def test_invalid_property(site):
    with pytest.raises(ValidationError):
        TypeAdapter(SiteURL).validate_python(site)


def test_sitemap_url_with_query_is_not_normalized():
    url = "https://cdn.example.net/maps/a%20b.xml?lang=fr&kind=books"
    assert TypeAdapter(HTTPURL).validate_python(url) == url


def test_query_uses_native_names_and_preserves_zero_offset():
    query = SearchAnalyticsQuery(startDate="2026-01-01", endDate="2026-01-02", startRow=0)
    assert query.model_dump(by_alias=True, exclude_none=True) == {
        "startDate": "2026-01-01",
        "endDate": "2026-01-02",
        "startRow": 0,
    }
    assert SearchAnalyticsQuery(start_date="2026-01-01", end_date="2026-01-02")


@pytest.mark.parametrize(
    "extra",
    [
        {"startDate": "2026-02-30"},
        {"endDate": "2025-12-31"},
        {"startDate": "20260101"},
        {"rowLimit": 0},
        {"rowLimit": 25001},
        {"rowLimit": True},
        {"startRow": -1},
        {"dimensions": ["page", "page"]},
        {"dimensions": ["unknown"]},
        {"orderBy": [{"fieldName": "clicks"}]},
        {"searchType": "WEB"},
        {"aggregationType": "byProperty", "dimensions": ["page"]},
        {"aggregationType": "byProperty", "type": "discover"},
        {"dimensionFilterGroups": [{"groupType": "or"}]},
        {"dimensionFilterGroups": [{"filters": [{"dimension": "date", "expression": "x"}]}]},
    ],
)
def test_invalid_queries(extra):
    args = {"startDate": "2026-01-01", "endDate": "2026-01-02", **extra}
    with pytest.raises(ValidationError):
        SearchAnalyticsQuery.model_validate(args)


def test_hourly_query_and_unbounded_nonnegative_offset():
    query = SearchAnalyticsQuery(
        startDate="2026-01-01",
        endDate="2026-01-02",
        dimensions=["hour"],
        dataState="hourly_all",
        startRow=100000,
        rowLimit=25000,
    )
    assert query.start_row == 100000
