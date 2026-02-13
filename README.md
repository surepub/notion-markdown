# notion-markdown

[![CI](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml/badge.svg)](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/surepub/notion-markdown/graph/badge.svg)](https://codecov.io/gh/surepub/notion-markdown)
[![PyPI](https://img.shields.io/pypi/v/notion-markdown)](https://pypi.org/project/notion-markdown/)
[![Python](https://img.shields.io/pypi/pyversions/notion-markdown)](https://pypi.org/project/notion-markdown/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Bidirectional conversion between Markdown and Notion API block objects. Fully typed, zero dependencies beyond [mistune](https://github.com/lepture/mistune).

```python
from notion_markdown import to_notion, to_markdown

# Markdown → Notion blocks
blocks = to_notion("# Hello\n\nSome **bold** text.")

# Notion blocks → Markdown
md = to_markdown(blocks)
# "# Hello\n\nSome **bold** text.\n"
```

## Installation

```bash
pip install notion-markdown
```

## CLI

### Markdown to Notion blocks

```bash
# File to stdout
notion-markdown to-notion README.md

# Pipe from stdin
cat README.md | notion-markdown to-notion

# Write to a file
notion-markdown to-notion README.md -o blocks.json

# Compact JSON (no indentation)
notion-markdown to-notion README.md --indent 0
```

### Notion blocks to Markdown

```bash
# JSON file to stdout
notion-markdown to-markdown blocks.json

# Pipe from stdin
cat blocks.json | notion-markdown to-markdown

# Write to a file
notion-markdown to-markdown blocks.json -o output.md
```

## Python API

### `to_notion()` — Markdown to Notion blocks

Takes a Markdown string and returns a list of Notion API block objects.
Pass them directly to [notion-client](https://github.com/ramnes/notion-sdk-py):

```python
from notion_client import Client
from notion_markdown import to_notion

notion = Client(auth="secret_...")
blocks = to_notion(open("README.md").read())

notion.pages.create(
    parent={"page_id": "..."},
    properties={"title": [{"text": {"content": "My Page"}}]},
    children=blocks,
)
```

### `to_markdown()` — Notion blocks to Markdown

Takes a list of Notion API block objects and returns a Markdown string.
Works with blocks from `to_notion()` or directly from the Notion API:

```python
from notion_markdown import to_notion, to_markdown

# From to_notion() output
blocks = to_notion("# Hello\n\nWorld")
md = to_markdown(blocks)

# From the Notion API
page_blocks = notion.blocks.children.list(block_id="...")["results"]
md = to_markdown(page_blocks)
```

### Roundtrip guarantee

The two functions are inverses — converting in either direction and back
produces identical output:

```python
from notion_markdown import to_notion, to_markdown

md = "# Title\n\nSome **bold** text.\n"
assert to_markdown(to_notion(md)) == md

blocks = to_notion(md)
assert to_notion(to_markdown(blocks)) == blocks
```

### Migration from `convert()`

In v0.7.0, `convert()` was renamed to `to_notion()` for consistency with
`to_markdown()`. The old `convert()` function still works but emits a
`DeprecationWarning`:

```python
# Old (deprecated)
from notion_markdown import convert
blocks = convert("# Hello")  # ⚠️ DeprecationWarning

# New
from notion_markdown import to_notion
blocks = to_notion("# Hello")
```

### Handling large documents (> 100 blocks)

The Notion API limits each request to 100 blocks. Split the list and append:

```python
from itertools import batched  # Python 3.12+

blocks = to_notion(long_markdown)

for i, chunk in enumerate(batched(blocks, 100)):
    if i == 0:
        page = notion.pages.create(
            parent={"page_id": "..."},
            properties={"title": [{"text": {"content": "Page"}}]},
            children=list(chunk),
        )
    else:
        notion.blocks.children.append(block_id=page["id"], children=list(chunk))
```

## Supported Markdown Elements

### Block-level

| Markdown | Notion block type |
|---|---|
| `# Heading` | `heading_1` |
| `## Heading` | `heading_2` |
| `### Heading` | `heading_3` |
| Paragraphs | `paragraph` |
| `- item` / `* item` | `bulleted_list_item` |
| `1. item` | `numbered_list_item` |
| `- [ ]` / `- [x]` | `to_do` |
| `` ```lang `` code fences | `code` (with language) |
| `---` | `divider` |
| `> quote` | `quote` |
| `\| table \|` | `table` + `table_row` |
| `![alt](url)` | `image` |
| `$$ expr $$` | `equation` |
| `<aside>` | `callout` |
| `<details><summary>` | `toggle` |

### Inline formatting

| Markdown | Notion annotation |
|---|---|
| `**bold**` / `__bold__` | `bold: true` |
| `*italic*` / `_italic_` | `italic: true` |
| `~~strike~~` | `strikethrough: true` |
| `` `code` `` | `code: true` |
| `[text](url)` | `text.link.url` |
| `$expr$` | inline `equation` |
| `<span underline="true">` | `underline: true` |
| `<span color="red">` | `color: "red"` |

Nested formatting is fully supported — `**bold *and italic* text**` produces
the correct flat list of rich-text items with accumulated annotations.

All conversions work in both directions: `to_notion()` and `to_markdown()` handle
every block and inline type listed above.

## Type Safety

Every return type is a `TypedDict`, giving you full IDE autocomplete and
`mypy --strict` compatibility. No `dict[str, Any]` in the public API.

```python
from notion_markdown import to_notion, to_markdown, NotionBlock, ParagraphBlock

blocks: list[NotionBlock] = to_notion("Hello **world**")
md: str = to_markdown(blocks)

# IDE knows blocks[0] could be ParagraphBlock, HeadingOneBlock, etc.
# and gives autocomplete for block["paragraph"]["rich_text"]
```

### Available types

All block types and rich-text types are exported:

```python
from notion_markdown import (
    # Block types
    ParagraphBlock, HeadingOneBlock, HeadingTwoBlock, HeadingThreeBlock,
    BulletedListItemBlock, NumberedListItemBlock, ToDoBlock,
    CodeBlock, QuoteBlock, CalloutBlock, ToggleBlock,
    DividerBlock, TableBlock, ImageBlock,
    EquationBlock, BookmarkBlock, EmbedBlock, VideoBlock,
    # Rich-text types
    RichText, RichTextText, RichTextEquation, RichTextAnnotations,
    # Union of all blocks
    NotionBlock,
)
```

## Code block language mapping

Common language aliases are automatically mapped to Notion's language identifiers:

| Input | Notion language |
|---|---|
| `py` | `python` |
| `js`, `jsx` | `javascript` |
| `ts`, `tsx` | `typescript` |
| `sh`, `zsh` | `shell` |
| `yml` | `yaml` |
| `rb` | `ruby` |
| `rs` | `rust` |
| `cpp`, `cc` | `c++` |
| `cs` | `c#` |
| (empty) | `plain text` |

## Development

```bash
# Clone and install
git clone https://github.com/surepub/notion-markdown.git
cd notion-markdown
uv venv && uv pip install -e . && uv pip install pytest pytest-cov ruff mypy

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=notion_markdown --cov-report=term-missing

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/ --strict
```

## License

MIT
