"""Bidirectional roundtrip snapshot tests.

These tests pin the **exact** output of both conversion directions so that
any future change to ``to_notion()`` or ``to_markdown()`` that breaks symmetry
is caught immediately.

For each fixture we test three properties:

1. **MD → Blocks → MD** (idempotent):
   ``to_markdown(to_notion(canonical_md)) == canonical_md``

2. **Blocks → MD → Blocks** (idempotent):
   ``to_notion(to_markdown(blocks)) == blocks``

3. **Stability** (double-roundtrip):
   A second roundtrip produces the exact same Markdown and blocks.

Every canonical Markdown string below is the *normalised* form — the stable
output after one ``to_markdown(to_notion(…))`` pass.  If a test fails, it means
the conversion contract changed and the canonical form needs to be reviewed
and intentionally updated.
"""

import pytest

from notion_markdown import to_markdown, to_notion

# ── Helpers for building rich-text fixtures concisely ─────────────────────


def _t(content):
    """Plain text rich-text item."""
    return {"type": "text", "text": {"content": content}}


def _t_ann(content, **annotations):
    """Text rich-text item with annotations."""
    return {"type": "text", "text": {"content": content}, "annotations": annotations}


def _t_link(content, url):
    """Text rich-text item with a link."""
    return {"type": "text", "text": {"content": content, "link": {"url": url}}}


def _t_link_ann(content, url, **annotations):
    """Text rich-text item with a link and annotations."""
    return {
        "type": "text",
        "text": {"content": content, "link": {"url": url}},
        "annotations": annotations,
    }


# ── Fixtures: (id, canonical_markdown, expected_blocks) ────────────────────
#
# ``expected_blocks`` is the exact ``convert(canonical_md)`` output.
# We inline them so that both directions are pinned.

FIXTURES: list[tuple[str, str, list]] = [
    # ── Paragraph ─────────────────────────────────────────────────────
    (
        "paragraph_plain",
        "Hello world\n",
        [{"type": "paragraph", "paragraph": {"rich_text": [_t("Hello world")]}}],
    ),
    (
        "paragraph_bold",
        "Some **bold** text.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Some "),
                        _t_ann("bold", bold=True),
                        _t(" text."),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_italic",
        "Some *italic* text.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Some "),
                        _t_ann("italic", italic=True),
                        _t(" text."),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_bold_italic",
        "Some ***bold italic*** text.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Some "),
                        _t_ann("bold italic", bold=True, italic=True),
                        _t(" text."),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_strikethrough",
        "Some ~~struck~~ text.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Some "),
                        _t_ann("struck", strikethrough=True),
                        _t(" text."),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_code",
        "Use `code` here.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Use "),
                        _t_ann("code", code=True),
                        _t(" here."),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_link",
        "[Google](https://google.com)\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [_t_link("Google", "https://google.com")],
                },
            },
        ],
    ),
    (
        "paragraph_bold_link",
        "[**bold link**](https://example.com)\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t_link_ann("bold link", "https://example.com", bold=True),
                    ],
                },
            },
        ],
    ),
    (
        "paragraph_inline_equation",
        "Text with $E=mc^2$ inline.\n",
        [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        _t("Text with "),
                        {"type": "equation", "equation": {"expression": "E=mc^2"}},
                        _t(" inline."),
                    ],
                },
            },
        ],
    ),
    # ── Headings ──────────────────────────────────────────────────────
    (
        "heading_1",
        "# Title\n",
        [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [_t("Title")], "is_toggleable": False},
            },
        ],
    ),
    (
        "heading_2",
        "## Subtitle\n",
        [
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [_t("Subtitle")], "is_toggleable": False},
            },
        ],
    ),
    (
        "heading_3",
        "### Detail\n",
        [
            {
                "type": "heading_3",
                "heading_3": {"rich_text": [_t("Detail")], "is_toggleable": False},
            },
        ],
    ),
    # ── Lists ─────────────────────────────────────────────────────────
    (
        "bulleted_list",
        "- one\n- two\n- three\n",
        [
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("one")]}},
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("two")]}},
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [_t("three")]}},
        ],
    ),
    (
        "numbered_list",
        "1. first\n1. second\n",
        [
            {
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [_t("first")]},
            },
            {
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [_t("second")]},
            },
        ],
    ),
    (
        "nested_bullet_list",
        "- parent\n    - child\n",
        [
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
        ],
    ),
    (
        "nested_numbered_list",
        "1. parent\n    1. child\n",
        [
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
        ],
    ),
    # ── To-do ─────────────────────────────────────────────────────────
    (
        "todo_items",
        "- [x] done\n- [ ] pending\n",
        [
            {"type": "to_do", "to_do": {"rich_text": [_t("done")], "checked": True}},
            {"type": "to_do", "to_do": {"rich_text": [_t("pending")], "checked": False}},
        ],
    ),
    # ── Code block ────────────────────────────────────────────────────
    (
        "code_block_python",
        "```python\nprint(1)\n```\n",
        [
            {
                "type": "code",
                "code": {
                    "rich_text": [_t("print(1)")],
                    "language": "python",
                },
            },
        ],
    ),
    (
        "code_block_plain",
        "```\nplain code\n```\n",
        [
            {
                "type": "code",
                "code": {
                    "rich_text": [_t("plain code")],
                    "language": "plain text",
                },
            },
        ],
    ),
    # ── Quote ─────────────────────────────────────────────────────────
    (
        "quote_simple",
        "> A wise quote\n",
        [{"type": "quote", "quote": {"rich_text": [_t("A wise quote")]}}],
    ),
    # ── Divider ───────────────────────────────────────────────────────
    (
        "divider",
        "---\n",
        [{"type": "divider", "divider": {}}],
    ),
    # ── Image ─────────────────────────────────────────────────────────
    (
        "image_with_alt",
        "![alt text](https://example.com/img.png)\n",
        [
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/img.png"},
                    "caption": [_t("alt text")],
                },
            },
        ],
    ),
    # ── Table ─────────────────────────────────────────────────────────
    (
        "table_with_header",
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n",
        [
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
        ],
    ),
    (
        "table_multi_row",
        "| A | B | C |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n",
        [
            {
                "type": "table",
                "table": {
                    "table_width": 3,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": [
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [[_t("A")], [_t("B")], [_t("C")]],
                            },
                        },
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [[_t("1")], [_t("2")], [_t("3")]],
                            },
                        },
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [[_t("4")], [_t("5")], [_t("6")]],
                            },
                        },
                    ],
                },
            },
        ],
    ),
    # ── Block equation ────────────────────────────────────────────────
    (
        "block_equation",
        "$$\nE=mc^2\n$$\n",
        [{"type": "equation", "equation": {"expression": "E=mc^2"}}],
    ),
    # ── Callout (aside) ───────────────────────────────────────────────
    (
        "callout_with_emoji",
        "<aside>\n\U0001f4a1 Important\n</aside>\n",
        [
            {
                "type": "callout",
                "callout": {
                    "rich_text": [_t("Important")],
                    "icon": {"emoji": "\U0001f4a1"},
                },
            },
        ],
    ),
    # ── Toggle ────────────────────────────────────────────────────────
    (
        "toggle",
        "<details><summary>Click</summary>Hidden</details>\n",
        [
            {
                "type": "toggle",
                "toggle": {
                    "rich_text": [_t("Click")],
                    "children": [
                        {
                            "type": "paragraph",
                            "paragraph": {"rich_text": [_t("Hidden")]},
                        },
                    ],
                },
            },
        ],
    ),
    # ── Mixed document ────────────────────────────────────────────────
    (
        "mixed_document",
        "# Title\n\nA paragraph.\n\n- bullet\n\n1. numbered\n\n---\n",
        [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [_t("Title")], "is_toggleable": False},
            },
            {"type": "paragraph", "paragraph": {"rich_text": [_t("A paragraph.")]}},
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [_t("bullet")]},
            },
            {
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [_t("numbered")]},
            },
            {"type": "divider", "divider": {}},
        ],
    ),
]


# ── Parametrized IDs for readable test output ────────────────────────────

_IDS = [f[0] for f in FIXTURES]


# ── Tests ─────────────────────────────────────────────────────────────────


class TestMarkdownToBlocksToMarkdown:
    """MD → Blocks → MD produces exactly the canonical Markdown."""

    @pytest.mark.parametrize(("name", "canonical_md", "expected_blocks"), FIXTURES, ids=_IDS)
    def test_md_to_blocks_to_md(self, name, canonical_md, expected_blocks):
        assert to_markdown(to_notion(canonical_md)) == canonical_md


class TestBlocksToMarkdownToBlocks:
    """Blocks → MD → Blocks produces exactly the original blocks."""

    @pytest.mark.parametrize(("name", "canonical_md", "expected_blocks"), FIXTURES, ids=_IDS)
    def test_blocks_to_md_to_blocks(self, name, canonical_md, expected_blocks):
        assert to_notion(to_markdown(expected_blocks)) == expected_blocks


class TestToNotionMatchesExpected:
    """to_notion(canonical_md) produces exactly the expected blocks."""

    @pytest.mark.parametrize(("name", "canonical_md", "expected_blocks"), FIXTURES, ids=_IDS)
    def test_to_notion_exact(self, name, canonical_md, expected_blocks):
        assert to_notion(canonical_md) == expected_blocks


class TestToMarkdownMatchesExpected:
    """to_markdown(expected_blocks) produces exactly the canonical Markdown."""

    @pytest.mark.parametrize(("name", "canonical_md", "expected_blocks"), FIXTURES, ids=_IDS)
    def test_to_markdown_exact(self, name, canonical_md, expected_blocks):
        assert to_markdown(expected_blocks) == canonical_md


class TestDoubleRoundtripStability:
    """Two full roundtrips produce identical output (no drift)."""

    @pytest.mark.parametrize(("name", "canonical_md", "expected_blocks"), FIXTURES, ids=_IDS)
    def test_double_roundtrip(self, name, canonical_md, expected_blocks):
        # First roundtrip
        blocks_1 = to_notion(canonical_md)
        md_1 = to_markdown(blocks_1)

        # Second roundtrip
        blocks_2 = to_notion(md_1)
        md_2 = to_markdown(blocks_2)

        assert md_1 == md_2
        assert blocks_1 == blocks_2
