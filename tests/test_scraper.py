from __future__ import annotations

import pytest

from concert_scraper.scraper import _validate_url, _looks_like_spa_shell, _build_fallback_urls


# ---------------------------------------------------------------------------
# _validate_url — SSRF protection
# ---------------------------------------------------------------------------


def test_validate_url_accepts_https():
    """Standard HTTPS URLs should pass validation."""
    _validate_url("https://example.com/events")


def test_validate_url_accepts_http():
    """Plain HTTP URLs should pass validation."""
    _validate_url("http://example.com/events")


def test_validate_url_rejects_non_http_scheme():
    """Non-HTTP schemes (file, ftp, javascript) should be rejected."""
    with pytest.raises(ValueError, match="scheme must be http or https"):
        _validate_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="scheme must be http or https"):
        _validate_url("ftp://example.com")


def test_validate_url_rejects_no_hostname():
    """URLs without a hostname should be rejected."""
    with pytest.raises(ValueError, match="no hostname"):
        _validate_url("http://")


def test_validate_url_rejects_private_ip():
    """Private/internal IPs should be rejected (SSRF protection)."""
    with pytest.raises(ValueError, match="private/reserved"):
        _validate_url("http://192.168.1.1/events")

    with pytest.raises(ValueError, match="private/reserved"):
        _validate_url("http://10.0.0.1/events")


def test_validate_url_rejects_loopback():
    """Loopback addresses should be rejected."""
    with pytest.raises(ValueError, match="private/reserved"):
        _validate_url("http://127.0.0.1/events")


def test_validate_url_rejects_link_local():
    """Link-local addresses should be rejected."""
    with pytest.raises(ValueError, match="private/reserved"):
        _validate_url("http://169.254.1.1/events")


def test_validate_url_allows_hostname():
    """Regular hostnames (not IPs) should pass — DNS resolution is not checked."""
    _validate_url("https://thepageant.com/events")


# ---------------------------------------------------------------------------
# _looks_like_spa_shell — SPA detection heuristic
# ---------------------------------------------------------------------------


def test_spa_shell_detects_empty_react_app():
    """An empty React shell with noscript should be detected as SPA."""
    html = """
    <html><head><title>App</title></head>
    <body><div id="root"></div><noscript>Enable JS</noscript></body>
    </html>
    """
    assert _looks_like_spa_shell(html) is True


def test_spa_shell_ignores_small_static_page():
    """A small but legitimate static HTML page should NOT be flagged as SPA."""
    html = """
    <html><head><title>Venue</title></head>
    <body><h1>Shows</h1><p>Friday: Jazz Night</p></body>
    </html>
    """
    assert _looks_like_spa_shell(html) is False


def test_spa_shell_ignores_large_page():
    """A large page with SPA indicators is not a shell if it has content."""
    body_content = "Event listing " * 200  # lots of text
    html = f"""
    <html><head></head>
    <body><div id="root">{body_content}</div><noscript>Enable JS</noscript></body>
    </html>
    """
    assert _looks_like_spa_shell(html) is False


def test_spa_shell_detects_empty_vue_app():
    """An empty Vue app shell should be detected."""
    html = """
    <html><head></head>
    <body><div id="app"></div><noscript>You need JavaScript.</noscript></body>
    </html>
    """
    assert _looks_like_spa_shell(html) is True


# ---------------------------------------------------------------------------
# _build_fallback_urls
# ---------------------------------------------------------------------------


def test_build_fallback_urls_generates_common_paths():
    """Should generate fallback URLs on the same domain."""
    urls = _build_fallback_urls("https://example.com/old-page")
    assert "https://example.com/events" in urls
    assert "https://example.com/calendar" in urls
    assert "https://example.com/shows" in urls


def test_build_fallback_urls_excludes_original_path():
    """The original URL's path should not appear in the fallback list."""
    urls = _build_fallback_urls("https://example.com/events")
    assert "https://example.com/events" not in urls
