"""Parse Markdown into Notion API block objects.

Uses `mistune <https://github.com/lepture/mistune>`_ (v3) to build an AST
from the Markdown source, then walks the tree to produce a list of Notion
block dicts that can be passed directly to ``notion-client``
``pages.create(children=…)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import mistune

from markdown_to_notion._html import parse_block_html, preprocess_notion_html
from markdown_to_notion._inline import _tok_children, _tok_raw, _tok_type, parse_inline

if TYPE_CHECKING:
    from markdown_to_notion._types import (
        HeadingData,
        NotionBlock,
        RichText,
        TableRowBlock,
        _Token,
    )

# ── Language normalisation ─────────────────────────────────────────────────

LANGUAGE_MAP: dict[str, str] = {
    "": "plain text",
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "sh": "shell",
    "zsh": "shell",
    "fish": "shell",
    "console": "shell",
    "yml": "yaml",
    "rb": "ruby",
    "rs": "rust",
    "cs": "c#",
    "csharp": "c#",
    "cpp": "c++",
    "cc": "c++",
    "cxx": "c++",
    "objc": "objective-c",
    "objective-c": "objective-c",
    "kt": "kotlin",
    "kts": "kotlin",
    "tex": "latex",
    "md": "markdown",
    "dockerfile": "docker",
    "proto": "protobuf",
    "hs": "haskell",
    "ex": "elixir",
    "exs": "elixir",
    "erl": "erlang",
    "fs": "f#",
    "fsharp": "f#",
    "pl": "perl",
    "ps1": "powershell",
    "psm1": "powershell",
    "vb": "visual basic",
    "wasm": "webassembly",
    "wat": "webassembly",
    "text": "plain text",
    "txt": "plain text",
    "plaintext": "plain text",
    "plain": "plain text",
}


# All language values the Notion API accepts for code blocks.
_NOTION_LANGUAGES: frozenset[str] = frozenset(
    {
        "abap",
        "agda",
        "arduino",
        "assembly",
        "bash",
        "basic",
        "bnf",
        "c",
        "c#",
        "c++",
        "clojure",
        "coffeescript",
        "coq",
        "css",
        "dart",
        "dhall",
        "diff",
        "docker",
        "ebnf",
        "elixir",
        "elm",
        "erlang",
        "f#",
        "flow",
        "fortran",
        "gherkin",
        "glsl",
        "go",
        "graphql",
        "groovy",
        "haskell",
        "html",
        "idris",
        "java",
        "javascript",
        "json",
        "julia",
        "kotlin",
        "latex",
        "less",
        "lisp",
        "livescript",
        "llvm ir",
        "lua",
        "makefile",
        "markdown",
        "markup",
        "matlab",
        "mathematica",
        "mermaid",
        "mizar",
        "nix",
        "notion formula",
        "objective-c",
        "ocaml",
        "pascal",
        "perl",
        "php",
        "plain text",
        "powershell",
        "prolog",
        "protobuf",
        "purescript",
        "python",
        "r",
        "racket",
        "reason",
        "ruby",
        "rust",
        "sass",
        "scala",
        "scheme",
        "scss",
        "shell",
        "solidity",
        "sql",
        "swift",
        "toml",
        "typescript",
        "vb.net",
        "verilog",
        "vhdl",
        "visual basic",
        "webassembly",
        "xml",
        "yaml",
        "java/c/c++/c#",
    }
)


def _normalize_language(info: str) -> str:
    """Turn a code-fence info string into a Notion language identifier."""
    if not info:
        return "plain text"
    lang = info.strip().lower().split()[0]
    normalised = LANGUAGE_MAP.get(lang, lang)
    return normalised if normalised in _NOTION_LANGUAGES else "plain text"


# ── Token attribute helpers ────────────────────────────────────────────────


def _attr_str(tok: _Token, key: str) -> str:
    attrs = tok.get("attrs")
    if attrs is None:
        return ""
    val = attrs.get(key)
    return val if isinstance(val, str) else ""


def _attr_int(tok: _Token, key: str, default: int = 0) -> int:
    attrs = tok.get("attrs")
    if attrs is None:
        return default
    val = attrs.get(key)
    return val if isinstance(val, int) else default


def _attr_bool(tok: _Token, key: str) -> bool | None:
    """Return ``True``/``False`` if key exists, ``None`` otherwise."""
    attrs = tok.get("attrs")
    if attrs is None:
        return None
    if key not in attrs:
        return None
    val = attrs.get(key)
    return bool(val)


# ── Inline helpers ─────────────────────────────────────────────────────────

_INLINE_TYPES = frozenset(
    {
        "text",
        "strong",
        "emphasis",
        "codespan",
        "strikethrough",
        "link",
        "image",
        "softbreak",
        "linebreak",
        "inline_math",
        "math",
        "inline_html",
        "html",
        "mark",
        "insert",
    }
)


def _is_inline_token(tok: _Token) -> bool:
    return _tok_type(tok) in _INLINE_TYPES


def _plain_text_item(content: str) -> RichText:
    """Create a minimal plain-text rich-text item."""
    return {"type": "text", "text": {"content": content}}


def _paragraph_block(rich_text: list[RichText]) -> NotionBlock:
    return {"type": "paragraph", "paragraph": {"rich_text": rich_text}}


# ── Block dispatch ─────────────────────────────────────────────────────────


def _convert_block(token: _Token) -> list[NotionBlock]:
    """Dispatch a single AST token to the appropriate converter."""
    ttype = _tok_type(token)
    if ttype == "paragraph":
        return _convert_paragraph(token)
    if ttype == "heading":
        return _convert_heading(token)
    if ttype == "list":
        return _convert_list(token)
    if ttype == "block_code":
        return [_convert_code_block(token)]
    if ttype == "thematic_break":
        return [_convert_thematic_break()]
    if ttype == "block_quote":
        return [_convert_block_quote(token)]
    if ttype == "table":
        return [_convert_table(token)]
    if ttype in ("block_math", "math_block"):
        return [_convert_equation(token)]
    if ttype == "block_html":
        return _convert_block_html(token)
    # blank_line, unknown → skip
    return []


# ── Paragraph ──────────────────────────────────────────────────────────────


def _is_standalone_image(token: _Token) -> bool:
    children = _tok_children(token)
    return len(children) == 1 and _tok_type(children[0]) == "image"


def _convert_paragraph(token: _Token) -> list[NotionBlock]:
    children = _tok_children(token)
    if _is_standalone_image(token):
        return _convert_image_block(children[0])
    rich_text = parse_inline(children)
    if not rich_text:
        return []
    return [_paragraph_block(rich_text)]


# ── Headings ───────────────────────────────────────────────────────────────


def _convert_heading(token: _Token) -> list[NotionBlock]:
    level = min(_attr_int(token, "level", 1), 3)
    rich_text = parse_inline(_tok_children(token))
    data: HeadingData = {"rich_text": rich_text, "is_toggleable": False}
    if level == 1:
        return [{"type": "heading_1", "heading_1": data}]
    if level == 2:
        return [{"type": "heading_2", "heading_2": data}]
    return [{"type": "heading_3", "heading_3": data}]


# ── Lists ──────────────────────────────────────────────────────────────────


def _convert_list(token: _Token) -> list[NotionBlock]:
    attrs = token.get("attrs")
    ordered = bool(attrs.get("ordered")) if attrs else False
    blocks: list[NotionBlock] = []
    for item in _tok_children(token):
        itype = _tok_type(item)
        if itype in ("list_item", "task_list_item"):
            is_task = itype == "task_list_item"
            blocks.extend(_convert_list_item(item, ordered=ordered, is_task=is_task))
    return blocks


def _convert_list_item(
    token: _Token,
    *,
    ordered: bool,
    is_task: bool,
) -> list[NotionBlock]:
    item_children = _tok_children(token)
    checked = _attr_bool(token, "checked")
    if is_task and checked is None:
        checked = False

    rich_text: list[RichText] = []
    nested_blocks: list[NotionBlock] = []

    if item_children and all(_is_inline_token(c) for c in item_children):
        rich_text = parse_inline(item_children)
    else:
        for child in item_children:
            ctype = _tok_type(child)
            if ctype in ("paragraph", "block_text"):
                if not rich_text:
                    rich_text = parse_inline(_tok_children(child))
                else:
                    child_rt = parse_inline(_tok_children(child))
                    if child_rt:
                        nested_blocks.append(_paragraph_block(child_rt))
            elif ctype == "list":
                nested_blocks.extend(_convert_list(child))
            else:
                nested_blocks.extend(_convert_block(child))

    if is_task:
        return [_build_todo(rich_text, bool(checked), nested_blocks)]
    if ordered:
        return [_build_numbered(rich_text, nested_blocks)]
    return [_build_bulleted(rich_text, nested_blocks)]


def _build_todo(
    rich_text: list[RichText],
    checked: bool,
    children: list[NotionBlock],
) -> NotionBlock:
    if children:
        return {
            "type": "to_do",
            "to_do": {"rich_text": rich_text, "checked": checked, "children": children},
        }
    return {"type": "to_do", "to_do": {"rich_text": rich_text, "checked": checked}}


def _build_bulleted(rich_text: list[RichText], children: list[NotionBlock]) -> NotionBlock:
    if children:
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": rich_text, "children": children},
        }
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich_text}}


def _build_numbered(rich_text: list[RichText], children: list[NotionBlock]) -> NotionBlock:
    if children:
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": rich_text, "children": children},
        }
    return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rich_text}}


# ── Code blocks ────────────────────────────────────────────────────────────


def _convert_code_block(token: _Token) -> NotionBlock:
    raw = _tok_raw(token).rstrip("\n")
    info = _attr_str(token, "info")
    language = _normalize_language(info)
    return {
        "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": raw}}],
            "language": language,
        },
    }


# ── Thematic break (divider) ──────────────────────────────────────────────


def _convert_thematic_break() -> NotionBlock:
    return {"type": "divider", "divider": {}}


# ── Block quotes ───────────────────────────────────────────────────────────


def _convert_block_quote(token: _Token) -> NotionBlock:
    block_children = _tok_children(token)
    rich_text: list[RichText] = []
    nested: list[NotionBlock] = []

    for child in block_children:
        ctype = _tok_type(child)
        if ctype == "paragraph" and not rich_text:
            rich_text = parse_inline(_tok_children(child))
        else:
            nested.extend(_convert_block(child))

    if nested:
        return {"type": "quote", "quote": {"rich_text": rich_text, "children": nested}}
    return {"type": "quote", "quote": {"rich_text": rich_text}}


# ── Tables ─────────────────────────────────────────────────────────────────


def _extract_row_cells(row_tok: _Token) -> list[list[RichText]]:
    return [
        parse_inline(_tok_children(child))
        for child in _tok_children(row_tok)
        if _tok_type(child) == "table_cell"
    ]


def _pad_row(cells: list[list[RichText]], width: int) -> list[list[RichText]]:
    """Ensure a row has exactly *width* cells (Notion API requirement)."""
    if len(cells) < width:
        return [*cells, *([[] for _ in range(width - len(cells))])]
    return cells


def _table_row(cells: list[list[RichText]], width: int = 0) -> TableRowBlock:
    padded = _pad_row(cells, width) if width else cells
    return {"type": "table_row", "table_row": {"cells": padded}}


def _convert_table(token: _Token) -> NotionBlock:
    rows: list[TableRowBlock] = []
    table_width = 0
    has_header = False

    for child in _tok_children(token):
        ctype = _tok_type(child)

        if ctype == "table_head":
            has_header = True
            cells = _extract_row_cells(child)
            if cells:
                table_width = max(table_width, len(cells))
                rows.append(_table_row(cells))

        elif ctype == "table_body":
            body_children = _tok_children(child)
            if body_children and _tok_type(body_children[0]) == "table_cell":
                all_cells: list[list[RichText]] = [
                    parse_inline(_tok_children(bc))
                    for bc in body_children
                    if _tok_type(bc) == "table_cell"
                ]
                width = table_width or len(all_cells)
                for i in range(0, len(all_cells), width):
                    row_cells = all_cells[i : i + width]
                    table_width = max(table_width, len(row_cells))
                    rows.append(_table_row(row_cells, table_width))
            else:
                for row_child in body_children:
                    cells = _extract_row_cells(row_child)
                    if cells:
                        table_width = max(table_width, len(cells))
                        rows.append(_table_row(cells, table_width))

    # Pad all rows to final table_width (header may have been added before width was known)
    final_width = table_width or 1
    padded_rows: list[TableRowBlock] = [
        _table_row(r["table_row"]["cells"], final_width) for r in rows
    ]

    return {
        "type": "table",
        "table": {
            "table_width": final_width,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": padded_rows,
        },
    }


# ── Image (standalone) ────────────────────────────────────────────────────


def _convert_image_block(token: _Token) -> list[NotionBlock]:
    url = _attr_str(token, "url") or _attr_str(token, "src")
    if not url:
        return []
    # Alt text can be in attrs or in children (mistune puts it in children)
    alt = _attr_str(token, "alt")
    if not alt:
        children = _tok_children(token)
        if children and _tok_type(children[0]) == "text":
            alt = _tok_raw(children[0])
    if alt:
        caption: list[RichText] = [_plain_text_item(alt)]
        return [
            {
                "type": "image",
                "image": {"type": "external", "external": {"url": url}, "caption": caption},
            }
        ]
    return [{"type": "image", "image": {"type": "external", "external": {"url": url}}}]


# ── Equation (block-level math) ───────────────────────────────────────────


def _convert_equation(token: _Token) -> NotionBlock:
    raw = _tok_raw(token).strip()
    return {"type": "equation", "equation": {"expression": raw}}


# ── Block HTML (best-effort) ──────────────────────────────────────────────


def _convert_block_html(token: _Token) -> list[NotionBlock]:
    raw = _tok_raw(token).strip()
    if not raw:
        return []
    # Try Notion-specific HTML patterns first
    notion_blocks = parse_block_html(raw)
    if notion_blocks is not None:
        return notion_blocks
    # Fall back to paragraph with raw text
    return [_paragraph_block([_plain_text_item(raw)])]


# ── Parser (cached) ───────────────────────────────────────────────────────

_MD = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough", "task_lists", "math"],
)


# ── Public entry point ─────────────────────────────────────────────────────


def parse(markdown: str) -> list[NotionBlock]:
    """Parse a Markdown string into a list of Notion API block objects.

    Uses *mistune* to parse the Markdown into an AST, then converts each
    AST node into the corresponding Notion block structure.  The returned
    list can be passed directly to ``notion-client``'s
    ``pages.create(children=…)`` or ``blocks.children.append(children=…)``.
    """
    preprocessed = preprocess_notion_html(markdown)
    raw_result = _MD(preprocessed)
    if not isinstance(raw_result, list):
        return []
    tokens = cast("list[_Token]", raw_result)

    blocks: list[NotionBlock] = []
    for token in tokens:
        blocks.extend(_convert_block(token))
    return blocks
