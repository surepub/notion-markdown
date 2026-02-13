"""Acid tests — complex real-world Markdown documents.

Inspired by the browser acid tests and Markdown kitchen-sink repos
(mxstbr/markdown-test-file, adamschwartz/github-markdown-kitchen-sink),
these tests exercise the full conversion pipeline with documents that
combine many features at once.

Each test asserts three things:
1. ``to_markdown(to_notion(md))`` produces a known canonical Markdown
2. ``to_notion(to_markdown(blocks))`` reproduces the same blocks
3. A second roundtrip is identical to the first (no drift)
"""

import pytest

from notion_markdown import to_markdown, to_notion

# ── Acid test documents ───────────────────────────────────────────────────
#
# Each entry is (id, canonical_markdown).  The canonical form is the stable
# normalised output — the result of one ``to_markdown(convert(…))`` pass.

ACID_TESTS: list[tuple[str, str]] = [
    # ── 1. Dense inline: every inline format in a single paragraph ────
    (
        "dense_inline",
        "This paragraph has **bold**, *italic*, ***bold italic***,"
        " ~~strikethrough~~, `code`,"
        " and a [link](https://example.com) all in one line.\n",
    ),
    # ── 2. Three-level nested bullet lists ────────────────────────────
    (
        "nested_lists_3_deep",
        "- Level 1a\n"
        "    - Level 2a\n"
        "        - Level 3a\n"
        "        - Level 3b\n"
        "    - Level 2b\n"
        "- Level 1b\n",
    ),
    # ── 3. List items with mixed inline formatting ────────────────────
    (
        "formatted_list_items",
        "- **Bold item** with `code`\n"
        "- *Italic item* with ~~strike~~\n"
        "- [Link item](https://example.com) here\n",
    ),
    # ── 4. Table with formatted cells (bold, italic, code, strike, link)
    (
        "table_formatted_cells",
        "| Feature | Status | Notes |\n"
        "| --- | --- | --- |\n"
        "| **Auth** | Done | Uses `JWT` tokens |\n"
        "| *Search* | In Progress | ~~Delayed~~ On track |\n"
        "| [Docs](https://example.com) | Pending | Needs review |\n",
    ),
    # ── 5. Blockquote with mixed inline formatting ────────────────────
    (
        "quote_with_formatting",
        "> The **quick** brown fox *jumped* over the `lazy` dog.\n",
    ),
    # ── 6. Full heading hierarchy with body paragraphs ────────────────
    (
        "heading_hierarchy",
        "# Main Title\n\n"
        "Introduction paragraph with **emphasis**.\n\n"
        "## Section One\n\n"
        "Content for section one.\n\n"
        "### Subsection A\n\n"
        "Details here.\n\n"
        "### Subsection B\n\n"
        "More details.\n\n"
        "## Section Two\n\n"
        "Final content.\n",
    ),
    # ── 7. Code blocks in multiple languages ──────────────────────────
    (
        "multi_language_code",
        '```python\ndef hello():\n    return "world"\n```\n\n'
        '```javascript\nconst hello = () => "world";\n```\n\n'
        "```sql\nSELECT * FROM users WHERE active = true;\n```\n",
    ),
    # ── 8. Nested todo items ──────────────────────────────────────────
    (
        "todo_nested",
        "- [x] Complete task\n"
        "    - [x] Subtask done\n"
        "    - [ ] Subtask pending\n"
        "- [ ] Incomplete task\n",
    ),
    # ── 9. Full README-style document (every block type) ──────────────
    (
        "full_readme",
        "# Project README\n\n"
        "A short **description** of the project.\n\n"
        "## Installation\n\n"
        "```bash\npip install my-package\n```\n\n"
        "## Features\n\n"
        "- Feature one\n"
        "- Feature two\n"
        "- Feature three\n\n"
        "1. Step one\n"
        "1. Step two\n"
        "1. Step three\n\n"
        "## Status\n\n"
        "| Component | Status |\n"
        "| --- | --- |\n"
        "| API | Done |\n"
        "| UI | WIP |\n\n"
        "---\n\n"
        "![logo](https://example.com/logo.png)\n\n"
        "## Math\n\n"
        "$$\n"
        "f(x) = \\sum_{i=0}^{n} x_i^2\n"
        "$$\n\n"
        "Inline math: $E=mc^2$ is famous.\n",
    ),
    # ── 10. Emphasis edge cases ───────────────────────────────────────
    (
        "emphasis_edges",
        "A **bold at start** of paragraph.\n\n"
        "End of paragraph is **bold**.\n\n"
        "Middle has *italic* word.\n\n"
        "***All three*** at once.\n\n"
        "Some ~~crossed out words~~ here.\n",
    ),
]

_IDS = [t[0] for t in ACID_TESTS]


# ── Test classes ──────────────────────────────────────────────────────────


class TestAcidRoundtripMdToBlocksToMd:
    """Canonical MD → Blocks → MD produces the exact same canonical MD."""

    @pytest.mark.parametrize(("name", "canonical_md"), ACID_TESTS, ids=_IDS)
    def test_md_roundtrip(self, name, canonical_md):
        assert to_markdown(to_notion(canonical_md)) == canonical_md


class TestAcidRoundtripBlocksToMdToBlocks:
    """Blocks → MD → Blocks produces the exact same blocks."""

    @pytest.mark.parametrize(("name", "canonical_md"), ACID_TESTS, ids=_IDS)
    def test_blocks_roundtrip(self, name, canonical_md):
        blocks = to_notion(canonical_md)
        assert to_notion(to_markdown(blocks)) == blocks


class TestAcidDoubleRoundtripStability:
    """Two full roundtrips produce identical output — no drift."""

    @pytest.mark.parametrize(("name", "canonical_md"), ACID_TESTS, ids=_IDS)
    def test_double_roundtrip(self, name, canonical_md):
        blocks_1 = to_notion(canonical_md)
        md_1 = to_markdown(blocks_1)
        blocks_2 = to_notion(md_1)
        md_2 = to_markdown(blocks_2)
        assert md_1 == md_2, "Markdown drifted on second roundtrip"
        assert blocks_1 == blocks_2, "Blocks drifted on second roundtrip"


_EXPECTED_COUNTS = {
    "dense_inline": 1,
    "nested_lists_3_deep": 2,
    "formatted_list_items": 3,
    "table_formatted_cells": 1,
    "quote_with_formatting": 1,
    "heading_hierarchy": 10,
    "multi_language_code": 3,
    "todo_nested": 2,
    "full_readme": 18,
    "emphasis_edges": 5,
}


class TestAcidBlockCounts:
    """Verify each document produces the expected number of blocks."""

    @pytest.mark.parametrize(("name", "canonical_md"), ACID_TESTS, ids=_IDS)
    def test_block_count(self, name, canonical_md):
        blocks = to_notion(canonical_md)
        assert len(blocks) == _EXPECTED_COUNTS[name]


class TestAcidBlockTypes:
    """Verify the full_readme doc contains every supported block type."""

    def test_full_readme_has_all_types(self):
        canonical = next(md for name, md in ACID_TESTS if name == "full_readme")
        blocks = to_notion(canonical)
        types = {b["type"] for b in blocks}
        expected = {
            "heading_1",
            "heading_2",
            "paragraph",
            "code",
            "bulleted_list_item",
            "numbered_list_item",
            "table",
            "divider",
            "image",
            "equation",
        }
        missing = expected - types
        assert not missing, f"Missing block types: {missing}"


class TestAcidInlineAnnotations:
    """Verify the dense_inline doc produces all annotation types."""

    def test_dense_inline_annotations(self):
        canonical = next(md for name, md in ACID_TESTS if name == "dense_inline")
        blocks = to_notion(canonical)
        rt = blocks[0]["paragraph"]["rich_text"]
        annotation_keys = set()
        has_link = False
        for item in rt:
            for key, val in item.get("annotations", {}).items():
                if val:
                    annotation_keys.add(key)
            if item.get("text", {}).get("link"):
                has_link = True
        expected = {"bold", "italic", "strikethrough", "code"}
        missing = expected - annotation_keys
        assert not missing, f"Missing annotations: {missing}"
        assert has_link, "Missing link in dense_inline"


class TestAcidTableFormattedCells:
    """Verify the table with formatted cells preserves all formatting."""

    def test_cell_formatting_preserved(self):
        canonical = next(md for name, md in ACID_TESTS if name == "table_formatted_cells")
        md_out = to_markdown(to_notion(canonical))
        # Bold cell
        assert "**Auth**" in md_out
        # Italic cell
        assert "*Search*" in md_out
        # Code in cell
        assert "`JWT`" in md_out
        # Strikethrough in cell
        assert "~~Delayed~~" in md_out
        # Link in cell
        assert "[Docs](https://example.com)" in md_out


class TestAcidNestedListDepth:
    """Verify 3-level nested lists produce correct indentation."""

    def test_three_level_indentation(self):
        canonical = next(md for name, md in ACID_TESTS if name == "nested_lists_3_deep")
        md_out = to_markdown(to_notion(canonical))
        lines = md_out.splitlines()
        # Level 1 — no indent
        assert any(line.startswith("- Level 1") for line in lines)
        # Level 2 — 4 spaces
        assert any(line.startswith("    - Level 2") for line in lines)
        # Level 3 — 8 spaces
        assert any(line.startswith("        - Level 3") for line in lines)
