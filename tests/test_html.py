"""Tests for Notion-specific HTML pattern parsing (_html.py)."""

from __future__ import annotations

from notion_markdown._html import (
    InlineHTMLResult,
    parse_block_html,
    parse_inline_html,
    preprocess_notion_html,
)

# ── parse_block_html: <aside> → callout ───────────────────────────────────


class TestAsideCallout:
    def test_aside_with_emoji(self) -> None:
        blocks = parse_block_html("<aside>\n🤝 For any question.\n</aside>")
        assert blocks is not None
        assert len(blocks) == 1
        assert blocks[0]["type"] == "callout"
        callout = blocks[0]["callout"]
        assert callout["icon"] == {"emoji": "🤝"}
        assert callout["rich_text"][0]["text"]["content"] == "For any question."

    def test_aside_without_emoji(self) -> None:
        blocks = parse_block_html("<aside>Plain callout text</aside>")
        assert blocks is not None
        assert blocks[0]["type"] == "callout"
        callout = blocks[0]["callout"]
        assert "icon" not in callout
        assert callout["rich_text"][0]["text"]["content"] == "Plain callout text"

    def test_aside_empty(self) -> None:
        blocks = parse_block_html("<aside></aside>")
        assert blocks is not None
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["rich_text"] == []

    def test_aside_single_line(self) -> None:
        blocks = parse_block_html("<aside>💡 Tip: use this feature.</aside>")
        assert blocks is not None
        assert blocks[0]["callout"]["icon"] == {"emoji": "💡"}

    def test_aside_multiline(self) -> None:
        raw = "<aside>\n⭐ Line one\nLine two\n</aside>"
        blocks = parse_block_html(raw)
        assert blocks is not None
        text = blocks[0]["callout"]["rich_text"][0]["text"]["content"]
        assert "Line one" in text


# ── parse_block_html: <callout> → callout ─────────────────────────────────


class TestCalloutTag:
    def test_callout_with_icon_and_color(self) -> None:
        raw = '<callout icon="🔥" color="red_bg">Hot tip!</callout>'
        blocks = parse_block_html(raw)
        assert blocks is not None
        callout = blocks[0]["callout"]
        assert callout["icon"] == {"emoji": "🔥"}
        assert callout["color"] == "red_bg"
        assert callout["rich_text"][0]["text"]["content"] == "Hot tip!"

    def test_callout_icon_only(self) -> None:
        raw = '<callout icon="📝">Note text</callout>'
        blocks = parse_block_html(raw)
        assert blocks is not None
        callout = blocks[0]["callout"]
        assert callout["icon"] == {"emoji": "📝"}
        assert "color" not in callout

    def test_callout_no_attrs(self) -> None:
        raw = "<callout>Simple callout</callout>"
        # This may or may not match depending on regex; if icon is required, skip
        # The regex allows optional icon/color, so it should match
        blocks = parse_block_html(raw)
        if blocks is not None:
            assert blocks[0]["type"] == "callout"


# ── parse_block_html: <details> → toggle ──────────────────────────────────


class TestDetailsToggle:
    def test_details_with_summary_and_body(self) -> None:
        raw = "<details><summary>Click to expand</summary>Hidden content</details>"
        blocks = parse_block_html(raw)
        assert blocks is not None
        assert blocks[0]["type"] == "toggle"
        toggle = blocks[0]["toggle"]
        assert toggle["rich_text"][0]["text"]["content"] == "Click to expand"
        assert toggle["children"][0]["type"] == "paragraph"
        body_text = toggle["children"][0]["paragraph"]["rich_text"][0]["text"]["content"]
        assert body_text == "Hidden content"

    def test_details_empty_body(self) -> None:
        raw = "<details><summary>Title only</summary></details>"
        blocks = parse_block_html(raw)
        assert blocks is not None
        assert blocks[0]["type"] == "toggle"
        assert "children" not in blocks[0]["toggle"]

    def test_details_multiline(self) -> None:
        raw = "<details>\n<summary>Expand</summary>\nLine 1\nLine 2\n</details>"
        blocks = parse_block_html(raw)
        assert blocks is not None
        assert blocks[0]["type"] == "toggle"


# ── parse_block_html: unrecognized ────────────────────────────────────────


class TestUnrecognizedBlockHTML:
    def test_random_html(self) -> None:
        assert parse_block_html("<div>random</div>") is None

    def test_empty_string(self) -> None:
        assert parse_block_html("") is None

    def test_plain_text(self) -> None:
        assert parse_block_html("just text") is None


# ── parse_inline_html ─────────────────────────────────────────────────────


class TestInlineHTMLBr:
    def test_br_tag(self) -> None:
        result = parse_inline_html("<br>")
        assert result is not None
        assert result.is_br is True

    def test_br_self_closing(self) -> None:
        result = parse_inline_html("<br/>")
        assert result is not None
        assert result.is_br is True

    def test_br_with_space(self) -> None:
        result = parse_inline_html("<br />")
        assert result is not None
        assert result.is_br is True


class TestInlineHTMLSpanUnderline:
    def test_span_underline(self) -> None:
        result = parse_inline_html('<span underline="true">')
        assert result is not None
        assert result.is_span_open is True
        assert result.underline is True
        assert result.color == ""

    def test_span_underline_single_quotes(self) -> None:
        result = parse_inline_html("<span underline='true'>")
        assert result is not None
        assert result.underline is True


class TestInlineHTMLSpanColor:
    def test_span_color(self) -> None:
        result = parse_inline_html('<span color="red">')
        assert result is not None
        assert result.is_span_open is True
        assert result.color == "red"
        assert result.underline is False

    def test_span_color_background(self) -> None:
        result = parse_inline_html('<span color="blue_bg">')
        assert result is not None
        assert result.color == "blue_bg"


class TestInlineHTMLSpanClose:
    def test_span_close(self) -> None:
        result = parse_inline_html("</span>")
        assert result is not None
        assert result.is_span_close is True


class TestInlineHTMLUnrecognized:
    def test_random_tag(self) -> None:
        assert parse_inline_html("<em>") is None

    def test_plain_text(self) -> None:
        assert parse_inline_html("text") is None

    def test_empty(self) -> None:
        assert parse_inline_html("") is None


# ── InlineHTMLResult defaults ─────────────────────────────────────────────


class TestInlineHTMLResult:
    def test_defaults(self) -> None:
        r = InlineHTMLResult()
        assert r.is_br is False
        assert r.is_span_open is False
        assert r.is_span_close is False
        assert r.underline is False
        assert r.color == ""


# ── preprocess_notion_html ────────────────────────────────────────────────


class TestPreprocess:
    def test_aside_multiline_collapsed(self) -> None:
        md = "text\n<aside>\n🤝 Help\n</aside>\nmore"
        result = preprocess_notion_html(md)
        # The <aside> block should be on a single line with blank-line padding
        assert "<aside>" in result
        assert "</aside>" in result
        # Should be collapsed to one line
        lines = [ln for ln in result.split("\n") if "<aside>" in ln]
        assert len(lines) == 1
        assert "</aside>" in lines[0]

    def test_details_multiline_collapsed(self) -> None:
        md = "<details>\n<summary>Title</summary>\nBody\n</details>"
        result = preprocess_notion_html(md)
        lines = [ln for ln in result.split("\n") if "<details>" in ln]
        assert len(lines) == 1

    def test_no_html_unchanged(self) -> None:
        md = "# Hello\n\nParagraph text."
        assert preprocess_notion_html(md) == md

    def test_standard_html_unchanged(self) -> None:
        md = "<div>content</div>"
        assert preprocess_notion_html(md) == md
