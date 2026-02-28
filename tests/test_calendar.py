from __future__ import annotations

from concert_scraper.calendar import _escape_applescript


# ---------------------------------------------------------------------------
# _escape_applescript — injection prevention
# ---------------------------------------------------------------------------


def test_escape_applescript_plain_text():
    """Plain text should pass through unchanged."""
    assert _escape_applescript("Jazz Night") == "Jazz Night"


def test_escape_applescript_escapes_double_quotes():
    """Double quotes must be escaped to prevent breaking out of string context."""
    assert _escape_applescript('He said "hello"') == 'He said \\"hello\\"'


def test_escape_applescript_escapes_backslashes():
    """Backslashes must be escaped before quotes to prevent escape sequence attacks."""
    assert _escape_applescript("path\\to\\file") == "path\\\\to\\\\file"


def test_escape_applescript_strips_newlines():
    """Newlines could break AppleScript string context and must be replaced."""
    result = _escape_applescript("line1\nline2\rline3\r\nline4")
    assert "\n" not in result
    assert "\r" not in result


def test_escape_applescript_strips_null_bytes():
    """Null bytes must be stripped to prevent truncation attacks."""
    result = _escape_applescript("before\x00after")
    assert "\x00" not in result
    assert "beforeafter" == result


def test_escape_applescript_strips_tabs():
    """Tabs should be replaced with spaces."""
    result = _escape_applescript("col1\tcol2")
    assert "\t" not in result


def test_escape_applescript_backslash_before_quote():
    """Backslash immediately before a quote must not create an unescaped quote.
    Input: \\\" should become \\\\\\" (escaped backslash + escaped quote)."""
    result = _escape_applescript('test\\"end')
    # The backslash is escaped first (\\\\), then the quote is escaped (\\")
    assert result == 'test\\\\\\"end'


def test_escape_applescript_combined_attack_string():
    """A string combining multiple injection vectors should be fully sanitized."""
    attack = 'title"\n-- evil code\r\x00'
    result = _escape_applescript(attack)
    assert '"' not in result or result.count('\\"') == result.count('"')
    assert "\n" not in result
    assert "\r" not in result
    assert "\x00" not in result
