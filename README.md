# notion-markdown

[![Lint & Format](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml/badge.svg?event=push&job=lint)](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml)
[![Type Check](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml/badge.svg?event=push&job=typecheck)](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml)
[![Tests](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml/badge.svg?event=push&job=test)](https://github.com/surepub/notion-markdown/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/surepub/notion-markdown/graph/badge.svg)](https://codecov.io/gh/surepub/notion-markdown)
[![PyPI](https://img.shields.io/pypi/v/notion-markdown)](https://pypi.org/project/notion-markdown/)
[![Python](https://img.shields.io/pypi/pyversions/notion-markdown)](https://pypi.org/project/notion-markdown/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Convert Markdown to Notion API block objects. Fully typed, zero dependencies beyond [mistune](https://github.com/lepture/mistune).

```python
from notion_markdown import convert

blocks = convert("# Hello\n\nSome **bold** text.")
# → list of Notion API block dicts, ready for notion-client
```

## Installation

```bash
pip install notion-markdown
```

## CLI

Convert a Markdown file to Notion API JSON:

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

## Python API

The library exposes a single function — `convert()` — that takes a Markdown
string and returns a list of Notion API block objects. Pass them directly to
[notion-client](https://github.com/ramnes/notion-sdk-py):

```python
from notion_client import Client
from notion_markdown import convert

notion = Client(auth="secret_...")
blocks = convert(open("README.md").read())

notion.pages.create(
    parent={"page_id": "..."},
    properties={"title": [{"text": {"content": "My Page"}}]},
    children=blocks,
)
```

### Handling large documents (> 100 blocks)

The Notion API limits each request to 100 blocks. Split the list and append:

```python
from itertools import batched  # Python 3.12+

blocks = convert(long_markdown)

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

### Inline formatting

| Markdown | Notion annotation |
|---|---|
| `**bold**` / `__bold__` | `bold: true` |
| `*italic*` / `_italic_` | `italic: true` |
| `~~strike~~` | `strikethrough: true` |
| `` `code` `` | `code: true` |
| `[text](url)` | `text.link.url` |
| `$expr$` | inline `equation` |

Nested formatting is fully supported — `**bold *and italic* text**` produces
the correct flat list of rich-text items with accumulated annotations.

## Type Safety

Every return type is a `TypedDict`, giving you full IDE autocomplete and
`mypy --strict` compatibility. No `dict[str, Any]` in the public API.

```python
from notion_markdown import convert, NotionBlock, ParagraphBlock

blocks: list[NotionBlock] = convert("Hello **world**")

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
    CodeBlock, QuoteBlock, DividerBlock, TableBlock, ImageBlock,
    EquationBlock, BookmarkBlock, EmbedBlock,
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
