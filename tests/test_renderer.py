"""Tests for _renderer.py — Notion blocks to Markdown rendering."""

from __future__ import annotations

from notion_markdown._renderer import render_blocks, to_markdown


class TestParagraph:
    def test_simple(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [_t("Hello world")]}},
        ]
        assert to_markdown(blocks) == "Hello world\n"

    def test_empty_rich_text(self):
        blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        assert to_markdown(blocks) == ""


class TestHeadings:
    def test_h1(self):
        data = {"rich_text": [_t("Title")], "is_toggleable": False}
        blocks = [{"type": "heading_1", "heading_1": data}]
        assert to_markdown(blocks) == "# Title\n"

    def test_h2(self):
        data = {"rich_text": [_t("Sub")], "is_toggleable": False}
        blocks = [{"type": "heading_2", "heading_2": data}]
        assert to_markdown(blocks) == "## Sub\n"

    def test_h3(self):
        data = {"rich_text": [_t("Detail")], "is_toggleable": False}
        blocks = [{"type": "heading_3", "heading_3": data}]
        assert to_markdown(blocks) == "### Detail\n"


class TestBulletedList:
    def test_single_item(self):
        blocks = [
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("item")]}},
        ]
        assert to_markdown(blocks) == "- item\n"

    def test_multiple_items(self):
        blocks = [
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("one")]}},
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("two")]}},
        ]
        assert to_markdown(blocks) == "- one\n- two\n"

    def test_nested_children(self):
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [_t("parent")],
                    "children": [
                        {
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": [_t("child")]},
                        },
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "- parent" in result
        assert "    - child" in result


class TestNumberedList:
    def test_items(self):
        blocks = [
            {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [_t("first")]}},
            {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [_t("second")]}},
        ]
        result = to_markdown(blocks)
        assert "1. first" in result
        assert "1. second" in result

    def test_nested_children(self):
        blocks = [
            {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [_t("parent")],
                    "children": [
                        {
                            "type": "numbered_list_item",
                            "numbered_list_item": {"rich_text": [_t("child")]},
                        },
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "1. parent" in result
        assert "    1. child" in result


class TestToDo:
    def test_checked(self):
        blocks = [
            {"type": "to_do", "to_do": {"rich_text": [_t("done")], "checked": True}},
        ]
        assert to_markdown(blocks) == "- [x] done\n"

    def test_unchecked(self):
        blocks = [
            {"type": "to_do", "to_do": {"rich_text": [_t("pending")], "checked": False}},
        ]
        assert to_markdown(blocks) == "- [ ] pending\n"

    def test_with_children(self):
        blocks = [
            {
                "type": "to_do",
                "to_do": {
                    "rich_text": [_t("parent")],
                    "checked": False,
                    "children": [
                        {
                            "type": "to_do",
                            "to_do": {"rich_text": [_t("sub")], "checked": True},
                        },
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "- [ ] parent" in result
        assert "    - [x] sub" in result


class TestCode:
    def test_with_language(self):
        blocks = [
            {
                "type": "code",
                "code": {"rich_text": [_t("print('hi')")], "language": "python"},
            },
        ]
        result = to_markdown(blocks)
        assert "```python" in result
        assert "print('hi')" in result
        assert result.rstrip().endswith("```")

    def test_plain_text_no_lang(self):
        blocks = [
            {"type": "code", "code": {"rich_text": [_t("some text")], "language": "plain text"}},
        ]
        result = to_markdown(blocks)
        assert "```\n" in result
        assert "some text" in result


class TestQuote:
    def test_simple(self):
        blocks = [{"type": "quote", "quote": {"rich_text": [_t("A wise saying")]}}]
        assert to_markdown(blocks) == "> A wise saying\n"

    def test_with_children(self):
        blocks = [
            {
                "type": "quote",
                "quote": {
                    "rich_text": [_t("main")],
                    "children": [
                        {"type": "paragraph", "paragraph": {"rich_text": [_t("child")]}},
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "> main" in result
        assert "> child" in result


class TestCallout:
    def test_with_emoji(self):
        blocks = [
            {
                "type": "callout",
                "callout": {
                    "rich_text": [_t("Important info")],
                    "icon": {"emoji": "💡"},
                },
            },
        ]
        result = to_markdown(blocks)
        assert "<aside>" in result
        assert "💡 Important info" in result
        assert "</aside>" in result

    def test_without_emoji(self):
        blocks = [
            {"type": "callout", "callout": {"rich_text": [_t("Note")]}},
        ]
        result = to_markdown(blocks)
        assert "<aside>" in result
        assert "Note" in result
        assert "</aside>" in result


class TestToggle:
    def test_with_body(self):
        blocks = [
            {
                "type": "toggle",
                "toggle": {
                    "rich_text": [_t("Click me")],
                    "children": [
                        {"type": "paragraph", "paragraph": {"rich_text": [_t("Hidden")]}},
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "<details><summary>Click me</summary>" in result
        assert "Hidden" in result
        assert "</details>" in result

    def test_without_body(self):
        blocks = [{"type": "toggle", "toggle": {"rich_text": [_t("Empty")]}}]
        result = to_markdown(blocks)
        assert "<details><summary>Empty</summary></details>" in result


class TestDivider:
    def test_divider(self):
        blocks = [{"type": "divider", "divider": {}}]
        assert to_markdown(blocks) == "---\n"


class TestTable:
    def test_with_header(self):
        blocks = [
            {
                "type": "table",
                "table": {
                    "table_width": 2,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": [
                        {
                            "type": "table_row",
                            "table_row": {"cells": [[_t("A")], [_t("B")]]},
                        },
                        {
                            "type": "table_row",
                            "table_row": {"cells": [[_t("1")], [_t("2")]]},
                        },
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "| A | B |" in result
        assert "| --- | --- |" in result
        assert "| 1 | 2 |" in result

    def test_without_header(self):
        blocks = [
            {
                "type": "table",
                "table": {
                    "table_width": 2,
                    "has_column_header": False,
                    "has_row_header": False,
                    "children": [
                        {
                            "type": "table_row",
                            "table_row": {"cells": [[_t("a")], [_t("b")]]},
                        },
                    ],
                },
            },
        ]
        result = to_markdown(blocks)
        assert "| a | b |" in result
        assert "---" not in result

    def test_empty_table(self):
        blocks = [
            {
                "type": "table",
                "table": {
                    "table_width": 0,
                    "has_column_header": False,
                    "has_row_header": False,
                    "children": [],
                },
            },
        ]
        # Empty table returns empty string — excluded from output
        result = to_markdown(blocks)
        assert result.strip() == ""


class TestImage:
    def test_with_caption(self):
        blocks = [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.png"},
                    "caption": [_t("A chart")],
                },
            },
        ]
        assert to_markdown(blocks) == "![A chart](https://example.com/img.png)\n"

    def test_without_caption(self):
        blocks = [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.png"},
                },
            },
        ]
        assert to_markdown(blocks) == "![](https://example.com/img.png)\n"


class TestEquation:
    def test_block_equation(self):
        blocks = [{"type": "equation", "equation": {"expression": "E=mc^2"}}]
        result = to_markdown(blocks)
        assert "$$" in result
        assert "E=mc^2" in result


class TestBookmark:
    def test_bookmark(self):
        blocks = [{"type": "bookmark", "bookmark": {"url": "https://example.com"}}]
        assert to_markdown(blocks) == "[https://example.com](https://example.com)\n"


class TestEmbed:
    def test_embed(self):
        blocks = [{"type": "embed", "embed": {"url": "https://example.com"}}]
        assert to_markdown(blocks) == "[https://example.com](https://example.com)\n"


class TestVideo:
    def test_video(self):
        blocks = [
            {
                "type": "video",
                "video": {
                    "type": "external",
                    "external": {"url": "https://example.com/vid.mp4"},
                },
            },
        ]
        assert to_markdown(blocks) == "![video](https://example.com/vid.mp4)\n"


class TestUnknownBlockType:
    def test_unknown_type_skipped(self):
        blocks = [{"type": "unknown_block", "unknown_block": {}}]
        assert to_markdown(blocks) == ""


class TestMixedDocument:
    def test_heading_then_paragraph(self):
        h_data = {"rich_text": [_t("Title")], "is_toggleable": False}
        blocks = [
            {"type": "heading_1", "heading_1": h_data},
            {"type": "paragraph", "paragraph": {"rich_text": [_t("Body")]}},
        ]
        result = to_markdown(blocks)
        assert "# Title" in result
        assert "Body" in result
        # Different types get blank line between them
        assert "\n\n" in result

    def test_blank_line_between_different_types(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [_t("para")]}},
            {"type": "divider", "divider": {}},
            {"type": "paragraph", "paragraph": {"rich_text": [_t("after")]}},
        ]
        result = to_markdown(blocks)
        lines = result.splitlines()
        assert "" in lines  # blank lines exist

    def test_no_blank_between_same_list_items(self):
        blocks = [
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("a")]}},
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("b")]}},
        ]
        result = to_markdown(blocks)
        assert result == "- a\n- b\n"


class TestRenderBlocks:
    def test_indent(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [_t("indented")]}},
        ]
        result = render_blocks(blocks, indent=4)
        assert result.startswith("    indented")


class TestQuoteMultiline:
    def test_multiline_rich_text(self):
        blocks = [
            {"type": "quote", "quote": {"rich_text": [_t("line1\nline2")]}},
        ]
        result = to_markdown(blocks)
        assert "> line1" in result
        assert "> line2" in result


# ── Helper ────────────────────────────────────────────────────────────────


def _t(content: str):
    """Shorthand for a plain-text rich_text item."""
    return {"type": "text", "text": {"content": content}}
