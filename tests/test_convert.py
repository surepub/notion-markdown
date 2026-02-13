"""End-to-end tests for the public convert() and to_markdown() APIs."""

from __future__ import annotations

from notion_markdown import convert, to_markdown


class TestConvertAPI:
    def test_returns_list(self) -> None:
        assert isinstance(convert("Hello"), list)

    def test_empty_returns_empty(self) -> None:
        assert convert("") == []

    def test_heading_and_paragraph(self) -> None:
        blocks = convert("# Title\n\nBody text.")
        assert len(blocks) == 2
        assert blocks[0]["type"] == "heading_1"
        assert blocks[1]["type"] == "paragraph"


class TestFullDocument:
    MARKDOWN = """\
# Project Status

This is the **summary** of Q3 results.

## Key Metrics

- Revenue: *$1.2M*
- Users: `50,000`
- ~~Target missed~~

### Action Items

1. Review budget
2. Update roadmap
3. Schedule all-hands

- [x] Finalize report
- [ ] Send to stakeholders

> Important: This data is **confidential**.

```python
def calculate_growth(current, previous):
    return (current - previous) / previous * 100
```

| Metric | Q2 | Q3 |
|--------|-----|-----|
| Revenue | 1.0 | 1.2 |
| Users | 40k | 50k |

---

![chart](https://example.com/chart.png)

$$
\\Delta = \\frac{Q3 - Q2}{Q2} \\times 100
$$
"""

    def test_full_document_types(self) -> None:
        blocks = convert(self.MARKDOWN)
        types = [b["type"] for b in blocks]
        expected = [
            "heading_1",
            "heading_2",
            "heading_3",
            "paragraph",
            "bulleted_list_item",
            "numbered_list_item",
            "to_do",
            "quote",
            "code",
            "table",
            "divider",
            "image",
            "equation",
        ]
        for t in expected:
            assert t in types, f"Missing block type: {t}"

    def test_full_document_block_count(self) -> None:
        assert len(convert(self.MARKDOWN)) >= 15

    def test_code_block_language(self) -> None:
        code_blocks = [b for b in convert(self.MARKDOWN) if b["type"] == "code"]
        assert code_blocks[0]["code"]["language"] == "python"

    def test_table_structure(self) -> None:
        tables = [b for b in convert(self.MARKDOWN) if b["type"] == "table"]
        table = tables[0]["table"]
        assert table["table_width"] == 3
        assert table["has_column_header"] is True
        assert len(table["children"]) == 3

    def test_todo_states(self) -> None:
        todos = [b for b in convert(self.MARKDOWN) if b["type"] == "to_do"]
        assert len(todos) == 2
        assert sum(1 for t in todos if t["to_do"]["checked"]) == 1
        assert sum(1 for t in todos if not t["to_do"]["checked"]) == 1

    def test_image_url(self) -> None:
        images = [b for b in convert(self.MARKDOWN) if b["type"] == "image"]
        assert images[0]["image"]["external"]["url"] == "https://example.com/chart.png"

    def test_strikethrough_in_list(self) -> None:
        bullet_items = [b for b in convert(self.MARKDOWN) if b["type"] == "bulleted_list_item"]
        found = any(
            rt.get("annotations", {}).get("strikethrough")
            for item in bullet_items
            for rt in item["bulleted_list_item"]["rich_text"]
        )
        assert found

    def test_inline_code_in_list(self) -> None:
        bullet_items = [b for b in convert(self.MARKDOWN) if b["type"] == "bulleted_list_item"]
        found = any(
            rt.get("annotations", {}).get("code")
            for item in bullet_items
            for rt in item["bulleted_list_item"]["rich_text"]
        )
        assert found


class TestNotionAPICompatibility:
    def test_block_has_type_and_data(self) -> None:
        block = convert("Hello world")[0]
        assert "type" in block
        assert block["type"] in block

    def test_rich_text_structure(self) -> None:
        rt = convert("**bold** text")[0]["paragraph"]["rich_text"]
        for item in rt:
            assert "type" in item
            assert item["type"] == "text"
            assert "content" in item["text"]

    def test_no_object_key(self) -> None:
        for block in convert("# Hello\n\nparagraph\n\n- item"):
            assert "object" not in block

    def test_heading_data_keys(self) -> None:
        heading = convert("# Test")[0]["heading_1"]
        assert "rich_text" in heading
        assert "is_toggleable" in heading

    def test_code_data_keys(self) -> None:
        code = convert("```python\ncode\n```")[0]["code"]
        assert "rich_text" in code
        assert "language" in code

    def test_table_data_keys(self) -> None:
        table = convert("| A | B |\n|---|---|\n| 1 | 2 |")[0]["table"]
        assert "table_width" in table
        assert "has_column_header" in table
        assert "has_row_header" in table
        assert "children" in table
        for row in table["children"]:
            assert row["type"] == "table_row"
            assert "cells" in row["table_row"]

    def test_image_data_keys(self) -> None:
        img = convert("![alt](https://example.com/img.png)")[0]["image"]
        assert img["type"] == "external"
        assert "url" in img["external"]

    def test_divider_data_keys(self) -> None:
        assert convert("---")[0]["divider"] == {}

    def test_todo_data_keys(self) -> None:
        todo = convert("- [x] done")[0]["to_do"]
        assert "rich_text" in todo
        assert isinstance(todo["checked"], bool)

    def test_link_in_rich_text(self) -> None:
        rt = convert("[Google](https://google.com)")[0]["paragraph"]["rich_text"]
        assert rt[0]["text"]["link"]["url"] == "https://google.com"

    def test_annotations_only_when_active(self) -> None:
        rt = convert("plain text")[0]["paragraph"]["rich_text"]
        assert "annotations" not in rt[0]

    def test_bold_annotation_only_has_bold(self) -> None:
        rt = convert("**bold**")[0]["paragraph"]["rich_text"]
        assert rt[0]["annotations"] == {"bold": True}


class TestToMarkdownAPI:
    def test_returns_string(self) -> None:
        blocks = convert("Hello")
        assert isinstance(to_markdown(blocks), str)

    def test_empty_returns_empty(self) -> None:
        assert to_markdown([]) == ""


class TestRoundtrip:
    """Verify that to_markdown(convert(md)) reproduces the original semantics."""

    def test_heading(self) -> None:
        md = "# Hello"
        result = to_markdown(convert(md))
        assert "# Hello" in result

    def test_paragraph_bold(self) -> None:
        md = "Some **bold** text."
        result = to_markdown(convert(md))
        assert "**bold**" in result
        assert "Some" in result

    def test_bulleted_list(self) -> None:
        md = "- one\n- two\n- three"
        result = to_markdown(convert(md))
        assert "- one" in result
        assert "- two" in result
        assert "- three" in result

    def test_numbered_list(self) -> None:
        md = "1. first\n2. second"
        result = to_markdown(convert(md))
        assert "1. first" in result
        assert "1. second" in result

    def test_todo(self) -> None:
        md = "- [x] done\n- [ ] pending"
        result = to_markdown(convert(md))
        assert "- [x] done" in result
        assert "- [ ] pending" in result

    def test_code_block(self) -> None:
        md = "```python\nprint('hi')\n```"
        result = to_markdown(convert(md))
        assert "```python" in result
        assert "print('hi')" in result

    def test_quote(self) -> None:
        md = "> A wise quote"
        result = to_markdown(convert(md))
        assert "> A wise quote" in result

    def test_divider(self) -> None:
        md = "---"
        result = to_markdown(convert(md))
        assert "---" in result

    def test_image(self) -> None:
        md = "![alt](https://example.com/img.png)"
        result = to_markdown(convert(md))
        assert "![alt](https://example.com/img.png)" in result

    def test_table(self) -> None:
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = to_markdown(convert(md))
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result

    def test_block_equation(self) -> None:
        md = "$$\nE=mc^2\n$$"
        result = to_markdown(convert(md))
        assert "$$" in result
        assert "E=mc^2" in result

    def test_inline_equation(self) -> None:
        md = "The formula $E=mc^2$ is famous."
        result = to_markdown(convert(md))
        assert "$E=mc^2$" in result

    def test_italic(self) -> None:
        md = "Some *italic* text."
        result = to_markdown(convert(md))
        assert "*italic*" in result

    def test_strikethrough(self) -> None:
        md = "Some ~~struck~~ text."
        result = to_markdown(convert(md))
        assert "~~struck~~" in result

    def test_inline_code(self) -> None:
        md = "Use `code` here."
        result = to_markdown(convert(md))
        assert "`code`" in result

    def test_link(self) -> None:
        md = "[Google](https://google.com)"
        result = to_markdown(convert(md))
        assert "[Google](https://google.com)" in result

    def test_full_document_roundtrip(self) -> None:
        md = (
            "# Title\n\n"
            "A paragraph with **bold** and *italic*.\n\n"
            "- item one\n"
            "- item two\n\n"
            "1. first\n"
            "2. second\n\n"
            "---\n\n"
            "```python\ncode()\n```\n\n"
            "> quote\n"
        )
        result = to_markdown(convert(md))
        assert "# Title" in result
        assert "**bold**" in result
        assert "*italic*" in result
        assert "- item one" in result
        assert "1. first" in result
        assert "---" in result
        assert "```python" in result
        assert "> quote" in result
