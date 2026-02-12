# markdown-to-notion

[![Lint & Format](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml/badge.svg?event=push&job=lint)](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml)
[![Type Check](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml/badge.svg?event=push&job=typecheck)](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml)
[![Tests](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml/badge.svg?event=push&job=test)](https://github.com/sureapp/markdown-to-notion/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sureapp/markdown-to-notion/graph/badge.svg)](https://codecov.io/gh/sureapp/markdown-to-notion)
[![PyPI](https://img.shields.io/pypi/v/markdown-to-notion)](https://pypi.org/project/markdown-to-notion/)
[![Python](https://img.shields.io/pypi/pyversions/markdown-to-notion)](https://pypi.org/project/markdown-to-notion/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Convert Markdown to Notion API block objects. Fully typed, zero dependencies beyond [mistune](https://github.com/lepture/mistune).

```python
from markdown_to_notion import convert

blocks = convert("# Hello\n\nSome **bold** text.")
# → list of Notion API block dicts, ready for notion-client
```

## Installation

```bash
pip install markdown-to-notion
```

## Usage

The library exposes a single function — `convert()` — that takes a Markdown
string and returns a list of Notion API block objects. Pass them directly to
[notion-client](https://github.com/ramnes/notion-sdk-py):

```python
from notion_client import Client
from markdown_to_notion import convert

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
from markdown_to_notion import convert, NotionBlock, ParagraphBlock

blocks: list[NotionBlock] = convert("Hello **world**")

# IDE knows blocks[0] could be ParagraphBlock, HeadingOneBlock, etc.
# and gives autocomplete for block["paragraph"]["rich_text"]
```

### Available types

All block types and rich-text types are exported:

```python
from markdown_to_notion import (
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
git clone https://github.com/sureapp/markdown-to-notion.git
cd markdown-to-notion
uv venv && uv pip install -e . && uv pip install pytest pytest-cov ruff mypy

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=markdown_to_notion --cov-report=term-missing

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/ --strict
```

## License

MIT
