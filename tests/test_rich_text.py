"""Tests for _rich_text.py — Notion rich_text to inline Markdown rendering."""

from __future__ import annotations

from notion_markdown._rich_text import render_rich_text


class TestPlainText:
    def test_single_text(self):
        items = [{"type": "text", "text": {"content": "hello"}}]
        assert render_rich_text(items) == "hello"

    def test_multiple_text(self):
        items = [
            {"type": "text", "text": {"content": "hello "}},
            {"type": "text", "text": {"content": "world"}},
        ]
        assert render_rich_text(items) == "hello world"

    def test_empty_list(self):
        assert render_rich_text([]) == ""

    def test_empty_content(self):
        items = [{"type": "text", "text": {"content": ""}}]
        assert render_rich_text(items) == ""


class TestBold:
    def test_bold(self):
        items = [
            {"type": "text", "text": {"content": "bold"}, "annotations": {"bold": True}},
        ]
        assert render_rich_text(items) == "**bold**"


class TestItalic:
    def test_italic(self):
        items = [
            {"type": "text", "text": {"content": "italic"}, "annotations": {"italic": True}},
        ]
        assert render_rich_text(items) == "*italic*"


class TestBoldItalic:
    def test_bold_italic(self):
        items = [
            {
                "type": "text",
                "text": {"content": "both"},
                "annotations": {"bold": True, "italic": True},
            },
        ]
        assert render_rich_text(items) == "***both***"


class TestStrikethrough:
    def test_strikethrough(self):
        items = [
            {
                "type": "text",
                "text": {"content": "struck"},
                "annotations": {"strikethrough": True},
            },
        ]
        assert render_rich_text(items) == "~~struck~~"


class TestCode:
    def test_code(self):
        items = [
            {"type": "text", "text": {"content": "code"}, "annotations": {"code": True}},
        ]
        assert render_rich_text(items) == "`code`"

    def test_code_with_link(self):
        items = [
            {
                "type": "text",
                "text": {"content": "code", "link": {"url": "https://example.com"}},
                "annotations": {"code": True},
            },
        ]
        assert render_rich_text(items) == "[`code`](https://example.com)"


class TestUnderline:
    def test_underline(self):
        items = [
            {
                "type": "text",
                "text": {"content": "under"},
                "annotations": {"underline": True},
            },
        ]
        assert render_rich_text(items) == '<span underline="true">under</span>'


class TestColor:
    def test_color(self):
        items = [
            {
                "type": "text",
                "text": {"content": "red"},
                "annotations": {"color": "red"},
            },
        ]
        assert render_rich_text(items) == '<span color="red">red</span>'


class TestLink:
    def test_link(self):
        items = [
            {
                "type": "text",
                "text": {"content": "Google", "link": {"url": "https://google.com"}},
            },
        ]
        assert render_rich_text(items) == "[Google](https://google.com)"

    def test_bold_link(self):
        items = [
            {
                "type": "text",
                "text": {"content": "link", "link": {"url": "https://example.com"}},
                "annotations": {"bold": True},
            },
        ]
        assert render_rich_text(items) == "[**link**](https://example.com)"


class TestEquation:
    def test_inline_equation(self):
        items = [{"type": "equation", "equation": {"expression": "E=mc^2"}}]
        assert render_rich_text(items) == "$E=mc^2$"


class TestStackedAnnotations:
    def test_bold_strikethrough(self):
        items = [
            {
                "type": "text",
                "text": {"content": "text"},
                "annotations": {"bold": True, "strikethrough": True},
            },
        ]
        assert render_rich_text(items) == "**~~text~~**"

    def test_italic_strikethrough(self):
        items = [
            {
                "type": "text",
                "text": {"content": "text"},
                "annotations": {"italic": True, "strikethrough": True},
            },
        ]
        assert render_rich_text(items) == "*~~text~~*"


class TestMixedContent:
    def test_mixed_plain_bold_italic(self):
        items = [
            {"type": "text", "text": {"content": "Hello "}},
            {
                "type": "text",
                "text": {"content": "bold"},
                "annotations": {"bold": True},
            },
            {"type": "text", "text": {"content": " and "}},
            {
                "type": "text",
                "text": {"content": "italic"},
                "annotations": {"italic": True},
            },
        ]
        assert render_rich_text(items) == "Hello **bold** and *italic*"
