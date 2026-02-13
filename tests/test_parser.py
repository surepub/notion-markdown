"""Tests for block-level Markdown → Notion block conversion."""

from __future__ import annotations

from notion_markdown._parser import parse


def _text(block: dict, key: str | None = None) -> str:
    """Extract the plain-text content from a block's rich_text."""
    k = key or block["type"]
    return "".join(rt["text"]["content"] for rt in block[k]["rich_text"] if rt["type"] == "text")


# ── Headings ───────────────────────────────────────────────────────────────


class TestHeadings:
    def test_h1(self) -> None:
        blocks = parse("# Title")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_1"
        assert _text(blocks[0]) == "Title"

    def test_h2(self) -> None:
        blocks = parse("## Subtitle")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"
        assert _text(blocks[0]) == "Subtitle"

    def test_h3(self) -> None:
        blocks = parse("### Section")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"
        assert _text(blocks[0]) == "Section"

    def test_h4_clamped_to_h3(self) -> None:
        blocks = parse("#### Deep heading")
        assert blocks[0]["type"] == "heading_3"

    def test_heading_with_inline(self) -> None:
        blocks = parse("# Hello **world**")
        rt = blocks[0]["heading_1"]["rich_text"]
        assert any(it.get("annotations", {}).get("bold") for it in rt)

    def test_heading_not_toggleable(self) -> None:
        blocks = parse("# Title")
        assert blocks[0]["heading_1"]["is_toggleable"] is False


# ── Paragraphs ─────────────────────────────────────────────────────────────


class TestParagraphs:
    def test_simple(self) -> None:
        blocks = parse("Hello world.")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert _text(blocks[0]) == "Hello world."

    def test_with_formatting(self) -> None:
        blocks = parse("Some **bold** and *italic* text.")
        rt = blocks[0]["paragraph"]["rich_text"]
        assert any(it.get("annotations", {}).get("bold") for it in rt)
        assert any(it.get("annotations", {}).get("italic") for it in rt)

    def test_multiple_paragraphs(self) -> None:
        blocks = parse("First paragraph.\n\nSecond paragraph.")
        assert len(blocks) == 2
        assert all(b["type"] == "paragraph" for b in blocks)


# ── Bulleted lists ─────────────────────────────────────────────────────────


class TestBulletedList:
    def test_dash_items(self) -> None:
        blocks = parse("- alpha\n- beta\n- gamma")
        assert len(blocks) == 3
        assert all(b["type"] == "bulleted_list_item" for b in blocks)
        assert _text(blocks[0]) == "alpha"
        assert _text(blocks[2]) == "gamma"

    def test_asterisk_items(self) -> None:
        blocks = parse("* one\n* two")
        assert all(b["type"] == "bulleted_list_item" for b in blocks)

    def test_nested_list(self) -> None:
        blocks = parse("- parent\n  - child")
        assert len(blocks) == 1
        parent = blocks[0]
        children = parent["bulleted_list_item"].get("children", [])
        assert len(children) == 1
        assert children[0]["type"] == "bulleted_list_item"
        assert _text(children[0]) == "child"

    def test_deeply_nested(self) -> None:
        blocks = parse("- a\n  - b\n    - c")
        child = blocks[0]["bulleted_list_item"]["children"][0]
        grandchild = child["bulleted_list_item"]["children"][0]
        assert _text(grandchild) == "c"

    def test_list_with_formatted_items(self) -> None:
        blocks = parse("- **bold** item\n- `code` item\n- ~~strike~~ item")
        assert len(blocks) == 3
        rt0 = blocks[0]["bulleted_list_item"]["rich_text"]
        assert any(it.get("annotations", {}).get("bold") for it in rt0)

    def test_list_item_with_code_block_child(self) -> None:
        """A list item can contain a code block as a nested child."""
        md = "- item\n\n  ```python\n  x = 1\n  ```"
        blocks = parse(md)
        assert len(blocks) >= 1
        # Collect all block types including nested children
        all_types: list[str] = []
        for b in blocks:
            all_types.append(b["type"])
            btype = b["type"]
            if btype in b:
                children = b[btype].get("children", [])
                all_types.extend(c["type"] for c in children)
        assert "code" in all_types


# ── Numbered lists ─────────────────────────────────────────────────────────


class TestNumberedList:
    def test_ordered(self) -> None:
        blocks = parse("1. first\n2. second\n3. third")
        assert len(blocks) == 3
        assert all(b["type"] == "numbered_list_item" for b in blocks)
        assert _text(blocks[0]) == "first"

    def test_nested_ordered(self) -> None:
        blocks = parse("1. outer\n   1. inner")
        children = blocks[0]["numbered_list_item"].get("children", [])
        assert len(children) == 1
        assert children[0]["type"] == "numbered_list_item"


# ── To-do / task list ─────────────────────────────────────────────────────


class TestToDo:
    def test_checked(self) -> None:
        blocks = parse("- [x] done task")
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["checked"] is True
        assert _text(blocks[0]) == "done task"

    def test_unchecked(self) -> None:
        blocks = parse("- [ ] pending task")
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["checked"] is False

    def test_mixed_list(self) -> None:
        blocks = parse("- [x] done\n- [ ] todo\n- normal item")
        types = [b["type"] for b in blocks]
        assert types.count("to_do") == 2
        assert types.count("bulleted_list_item") == 1

    def test_todo_with_nested_list(self) -> None:
        """A todo item with nested sub-items gets children."""
        md = "- [x] parent\n  - sub-item"
        blocks = parse(md)
        assert blocks[0]["type"] == "to_do"
        children = blocks[0]["to_do"].get("children", [])
        assert len(children) >= 1


# ── Code blocks ────────────────────────────────────────────────────────────


class TestCodeBlock:
    def test_fenced_with_language(self) -> None:
        blocks = parse("```python\nprint('hi')\n```")
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert "print('hi')" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_fenced_without_language(self) -> None:
        blocks = parse("```\nplain code\n```")
        assert blocks[0]["code"]["language"] == "plain text"

    def test_language_aliases(self) -> None:
        aliases = {
            "js": "javascript",
            "ts": "typescript",
            "sh": "shell",
            "yml": "yaml",
            "rb": "ruby",
            "rs": "rust",
            "cpp": "c++",
            "cs": "c#",
        }
        for alias, expected in aliases.items():
            blocks = parse(f"```{alias}\ncode\n```")
            assert blocks[0]["code"]["language"] == expected, f"Failed for alias {alias}"

    def test_multiline_code(self) -> None:
        md = "```python\ndef foo():\n    return 42\n```"
        blocks = parse(md)
        code = blocks[0]["code"]["rich_text"][0]["text"]["content"]
        assert "def foo():" in code
        assert "return 42" in code


# ── Divider ────────────────────────────────────────────────────────────────


class TestDivider:
    def test_triple_dash(self) -> None:
        blocks = parse("---")
        assert blocks[0]["type"] == "divider"
        assert blocks[0]["divider"] == {}

    def test_triple_asterisk(self) -> None:
        assert parse("***")[0]["type"] == "divider"

    def test_triple_underscore(self) -> None:
        assert parse("___")[0]["type"] == "divider"


# ── Block quotes ───────────────────────────────────────────────────────────


class TestBlockQuote:
    def test_simple(self) -> None:
        blocks = parse("> quoted text")
        assert blocks[0]["type"] == "quote"
        assert _text(blocks[0]) == "quoted text"

    def test_multiline_quote(self) -> None:
        blocks = parse("> line 1\n> line 2")
        assert blocks[0]["type"] == "quote"

    def test_quote_with_formatting(self) -> None:
        blocks = parse("> **bold** quote")
        rt = blocks[0]["quote"]["rich_text"]
        assert any(it.get("annotations", {}).get("bold") for it in rt)

    def test_multi_paragraph_quote(self) -> None:
        blocks = parse("> First para\n>\n> Second para")
        assert len(blocks) == 1
        quote = blocks[0]
        children = quote["quote"].get("children", [])
        assert len(children) >= 1

    def test_quote_with_nested_list(self) -> None:
        blocks = parse("> text\n>\n> - item")
        assert blocks[0]["type"] == "quote"


# ── Tables ─────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple_table(self) -> None:
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        blocks = parse(md)
        table = blocks[0]
        assert table["type"] == "table"
        assert table["table"]["table_width"] == 2
        assert table["table"]["has_column_header"] is True
        assert table["table"]["has_row_header"] is False
        assert len(table["table"]["children"]) == 2

    def test_table_cells_content(self) -> None:
        md = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"
        blocks = parse(md)
        rows = blocks[0]["table"]["children"]
        assert rows[0]["table_row"]["cells"][0][0]["text"]["content"] == "Col1"
        assert rows[1]["table_row"]["cells"][1][0]["text"]["content"] == "B"

    def test_table_with_formatting(self) -> None:
        md = "| Normal | **Bold** |\n|--------|----------|\n| plain  | *italic* |"
        blocks = parse(md)
        header_bold_cell = blocks[0]["table"]["children"][0]["table_row"]["cells"][1]
        assert any(it.get("annotations", {}).get("bold") for it in header_bold_cell)

    def test_three_column_table(self) -> None:
        md = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |"
        assert parse(md)[0]["table"]["table_width"] == 3

    def test_multi_row_table(self) -> None:
        md = "| H |\n|---|\n| R1 |\n| R2 |\n| R3 |"
        assert len(parse(md)[0]["table"]["children"]) == 4


# ── Images ─────────────────────────────────────────────────────────────────


class TestImage:
    def test_standalone_image(self) -> None:
        blocks = parse("![alt text](https://example.com/img.png)")
        assert blocks[0]["type"] == "image"
        assert blocks[0]["image"]["type"] == "external"
        assert blocks[0]["image"]["external"]["url"] == "https://example.com/img.png"

    def test_image_no_alt(self) -> None:
        blocks = parse("![](https://example.com/img.png)")
        assert blocks[0]["type"] == "image"
        assert "caption" not in blocks[0]["image"]

    def test_image_with_alt_caption(self) -> None:
        blocks = parse("![my caption](https://example.com/img.png)")
        caption = blocks[0]["image"].get("caption", [])
        assert len(caption) == 1
        assert caption[0]["text"]["content"] == "my caption"


# ── Block math ─────────────────────────────────────────────────────────────


class TestBlockMath:
    def test_equation_block(self) -> None:
        blocks = parse("$$\nE = mc^2\n$$")
        assert blocks[0]["type"] == "equation"
        assert blocks[0]["equation"]["expression"] == "E = mc^2"


# ── Block HTML ─────────────────────────────────────────────────────────────


class TestBlockHTML:
    def test_html_block_becomes_paragraph(self) -> None:
        blocks = parse("<div>hello</div>")
        assert len(blocks) >= 1
        # Should be converted to a paragraph with the raw HTML
        para_blocks = [b for b in blocks if b["type"] == "paragraph"]
        assert len(para_blocks) >= 1
        text = "".join(
            rt["text"]["content"]
            for rt in para_blocks[0]["paragraph"]["rich_text"]
            if rt["type"] == "text"
        )
        assert "hello" in text

    def test_empty_html_block_skipped(self) -> None:
        """An empty HTML block produces no output."""
        from notion_markdown._parser import _convert_block_html

        result = _convert_block_html({"type": "block_html", "raw": ""})
        assert result == []


# ── Callout (from <aside>) ─────────────────────────────────────────────────


class TestCallout:
    def test_aside_callout_with_emoji(self) -> None:
        blocks = parse("<aside>\n🤝 Please reach out.\n</aside>")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["icon"] == {"emoji": "🤝"}

    def test_aside_callout_text(self) -> None:
        blocks = parse("<aside>\n💡 Tip: check the docs.\n</aside>")
        text = blocks[0]["callout"]["rich_text"][0]["text"]["content"]
        assert "Tip: check the docs." in text

    def test_aside_callout_no_emoji(self) -> None:
        blocks = parse("<aside>Just a note.</aside>")
        assert blocks[0]["type"] == "callout"
        assert "icon" not in blocks[0]["callout"]

    def test_callout_tag_with_attrs(self) -> None:
        blocks = parse('<callout icon="🔥" color="red_bg">Hot tip!</callout>')
        assert len(blocks) == 1
        callout = blocks[0]["callout"]
        assert callout["icon"] == {"emoji": "🔥"}
        assert callout["color"] == "red_bg"
        assert callout["rich_text"][0]["text"]["content"] == "Hot tip!"


# ── Toggle (from <details>) ───────────────────────────────────────────────


class TestToggle:
    def test_details_toggle(self) -> None:
        blocks = parse("<details><summary>Click me</summary>Secret content</details>")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "toggle"
        toggle = blocks[0]["toggle"]
        assert toggle["rich_text"][0]["text"]["content"] == "Click me"
        assert (
            toggle["children"][0]["paragraph"]["rich_text"][0]["text"]["content"]
            == "Secret content"
        )

    def test_details_empty_body(self) -> None:
        blocks = parse("<details><summary>Title</summary></details>")
        assert blocks[0]["type"] == "toggle"
        assert "children" not in blocks[0]["toggle"]

    def test_multiline_details(self) -> None:
        md = "<details>\n<summary>Expand</summary>\nSome body text.\n</details>"
        blocks = parse(md)
        assert blocks[0]["type"] == "toggle"


# ── Mixed standard markdown + Notion HTML ──────────────────────────────────


class TestMixedContent:
    def test_callout_between_paragraphs(self) -> None:
        md = "Before.\n\n<aside>\n💡 Note\n</aside>\n\nAfter."
        blocks = parse(md)
        types = [b["type"] for b in blocks]
        assert "paragraph" in types
        assert "callout" in types

    def test_toggle_after_heading(self) -> None:
        md = "# Title\n\n<details><summary>FAQ</summary>Answer here</details>"
        blocks = parse(md)
        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "toggle" in types

    def test_full_notion_export_document(self) -> None:
        """Test a realistic Notion export with mixed content."""
        md = """\
# Project Notes

Some **bold** and *italic* text.

<aside>
🤝 For any question, reach out to the team.
</aside>

## Steps

1. First step
2. Second step with [link](https://example.com)

- [x] Done
- [ ] Pending

<details><summary>Technical Details</summary>
Implementation notes go here.
</details>

```python
def hello():
    return "world"
```

---

| Col1 | Col2 |
|------|------|
| A    | B    |

format: has ~~strike~~, <span underline="true">under</span>, `code`
"""
        blocks = parse(md)
        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "heading_2" in types
        assert "paragraph" in types
        assert "callout" in types
        assert "numbered_list_item" in types
        assert "to_do" in types
        assert "toggle" in types
        assert "code" in types
        assert "divider" in types
        assert "table" in types


# ── Edge cases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_string(self) -> None:
        assert parse("") == []

    def test_whitespace_only(self) -> None:
        assert parse("   \n\n   ") == []

    def test_link_in_paragraph(self) -> None:
        blocks = parse("[click here](https://example.com)")
        rt = blocks[0]["paragraph"]["rich_text"]
        assert rt[0]["text"]["link"]["url"] == "https://example.com"

    def test_multiple_block_types(self) -> None:
        md = "# Title\n\nParagraph.\n\n- item\n\n```py\ncode\n```\n\n---"
        blocks = parse(md)
        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "paragraph" in types
        assert "bulleted_list_item" in types
        assert "code" in types
        assert "divider" in types

    def test_unknown_block_type_ignored(self) -> None:
        """Unknown token types produce no output."""
        from notion_markdown._parser import _convert_block

        result = _convert_block({"type": "some_unknown_type"})
        assert result == []

    def test_blank_line_token_ignored(self) -> None:
        """Blank line tokens between blocks are skipped."""
        blocks = parse("text\n\n\n\nmore text")
        types = [b["type"] for b in blocks]
        assert "blank_line" not in types

    def test_loose_list_multiple_paragraphs(self) -> None:
        """A loose list item with multiple paragraphs."""
        md = "- First paragraph\n\n  Second paragraph"
        blocks = parse(md)
        assert len(blocks) >= 1
        # The first item should have the first para's text, second para as child
        item = blocks[0]
        btype = item["type"]
        assert btype in ("bulleted_list_item", "paragraph")

    def test_list_item_other_block_child(self) -> None:
        """A list item with a block quote as child."""
        md = "- item\n\n  > quoted"
        blocks = parse(md)
        assert len(blocks) >= 1

    def test_image_with_no_url(self) -> None:
        """An image token with no URL produces no block."""
        from notion_markdown._parser import _convert_image_block

        result = _convert_image_block({"type": "image", "attrs": {}})
        assert result == []

    def test_non_list_mistune_return(self) -> None:
        """If mistune returns a string (non-AST), parse returns []."""
        from unittest.mock import patch

        with patch("notion_markdown._parser._MD") as mock_md:
            mock_md.return_value = "<p>html</p>"
            result = parse("anything")
            assert result == []


# ── Attr helpers ───────────────────────────────────────────────────────────


class TestCoverageEdgeCases:
    """Tests targeting specific uncovered code paths."""

    def test_empty_paragraph_skipped(self) -> None:
        """A paragraph with no parseable content produces no block (line 191)."""
        from notion_markdown._parser import _convert_paragraph

        # A paragraph token whose children produce no rich_text
        result = _convert_paragraph({"type": "paragraph", "children": []})
        assert result == []

    def test_task_list_item_without_checked_attr(self) -> None:
        """A task_list_item token without a checked attr defaults to False (line 233)."""
        from notion_markdown._parser import _convert_list_item

        tok = {
            "type": "task_list_item",
            "children": [
                {"type": "block_text", "children": [{"type": "text", "raw": "item"}]},
            ],
            "attrs": {},
        }
        result = _convert_list_item(tok, ordered=False, is_task=True)
        assert result[0]["type"] == "to_do"
        assert result[0]["to_do"]["checked"] is False

    def test_tight_list_inline_children(self) -> None:
        """Tight list items have inline tokens directly as children (line 239)."""
        from notion_markdown._parser import _convert_list_item

        tok = {
            "type": "list_item",
            "children": [{"type": "text", "raw": "direct text"}],
        }
        result = _convert_list_item(tok, ordered=False, is_task=False)
        assert result[0]["type"] == "bulleted_list_item"
        rt = result[0]["bulleted_list_item"]["rich_text"]
        assert rt[0]["text"]["content"] == "direct text"

    def test_table_rows_padded_to_width(self) -> None:
        """Ragged rows are padded to table_width for Notion API compliance."""
        from notion_markdown._parser import _pad_row

        cells: list[list] = [[{"type": "text", "text": {"content": "A"}}]]
        padded = _pad_row(cells, 3)
        assert len(padded) == 3
        assert padded[0] == cells[0]
        assert padded[1] == []
        assert padded[2] == []

    def test_pad_row_no_change_when_full(self) -> None:
        from notion_markdown._parser import _pad_row

        cells: list[list] = [[], []]
        assert _pad_row(cells, 2) is cells

    def test_table_body_direct_cells(self) -> None:
        """Table body with direct table_cell children instead of table_row (lines 369-378)."""
        from notion_markdown._parser import _convert_table

        tok = {
            "type": "table",
            "children": [
                {
                    "type": "table_head",
                    "children": [
                        {"type": "table_cell", "children": [{"type": "text", "raw": "H1"}]},
                        {"type": "table_cell", "children": [{"type": "text", "raw": "H2"}]},
                    ],
                },
                {
                    "type": "table_body",
                    "children": [
                        {"type": "table_cell", "children": [{"type": "text", "raw": "A"}]},
                        {"type": "table_cell", "children": [{"type": "text", "raw": "B"}]},
                        {"type": "table_cell", "children": [{"type": "text", "raw": "C"}]},
                        {"type": "table_cell", "children": [{"type": "text", "raw": "D"}]},
                    ],
                },
            ],
        }
        result = _convert_table(tok)
        table = result["table"]
        assert table["table_width"] == 2
        # Header row + 2 body rows (4 cells / 2 width)
        assert len(table["children"]) == 3


class TestAttrHelpers:
    def test_attr_str_missing_attrs(self) -> None:
        from notion_markdown._parser import _attr_str

        assert _attr_str({"type": "x"}, "url") == ""

    def test_attr_str_non_string_value(self) -> None:
        from notion_markdown._parser import _attr_str

        assert _attr_str({"type": "x", "attrs": {"url": 42}}, "url") == ""

    def test_attr_int_missing_attrs(self) -> None:
        from notion_markdown._parser import _attr_int

        assert _attr_int({"type": "x"}, "level", 5) == 5

    def test_attr_int_non_int_value(self) -> None:
        from notion_markdown._parser import _attr_int

        assert _attr_int({"type": "x", "attrs": {"level": "abc"}}, "level", 1) == 1

    def test_attr_bool_missing_attrs(self) -> None:
        from notion_markdown._parser import _attr_bool

        assert _attr_bool({"type": "x"}, "checked") is None

    def test_attr_bool_missing_key(self) -> None:
        from notion_markdown._parser import _attr_bool

        assert _attr_bool({"type": "x", "attrs": {"other": True}}, "checked") is None

    def test_attr_bool_present(self) -> None:
        from notion_markdown._parser import _attr_bool

        assert _attr_bool({"type": "x", "attrs": {"checked": True}}, "checked") is True
        assert _attr_bool({"type": "x", "attrs": {"checked": False}}, "checked") is False
