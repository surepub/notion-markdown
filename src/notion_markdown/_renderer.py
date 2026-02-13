"""Render Notion API block objects back to Markdown.

This is the inverse of :mod:`notion_markdown._parser`.  Each Notion block
type is dispatched to a renderer function that returns one or more lines
of Markdown text.

Public entry point: :func:`to_markdown`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from notion_markdown._rich_text import render_rich_text

# Use the same "cast to dict[str, Any]" technique as _rich_text.py to
# work around TypedDict union limitations under mypy --strict.


def to_markdown(blocks: list[Any]) -> str:
    """Convert a list of Notion API block objects to a Markdown string.

    Parameters
    ----------
    blocks:
        Notion block dicts (as returned by :func:`notion_markdown.to_notion`
        or the Notion API).

    Returns
    -------
    str
        Markdown text.
    """
    return render_blocks(blocks, indent=0)


def render_blocks(blocks: list[Any], indent: int = 0) -> str:
    """Render a list of Notion blocks into Markdown.

    Parameters
    ----------
    blocks:
        Notion blocks to render.
    indent:
        The current indentation level (number of spaces to prepend to each
        line for nested list children).

    Returns
    -------
    str
        Markdown text with a trailing newline.
    """
    parts: list[str] = []
    prev_type = ""

    for block in blocks:
        d: dict[str, Any] = cast("dict[str, Any]", block)
        block_type: str = d.get("type", "")
        data: dict[str, Any] = d.get(block_type, {})

        # Insert blank line between different block types (but not between
        # consecutive list items of the same type).
        if parts and not _is_same_list_group(prev_type, block_type):
            parts.append("")

        rendered = _render_block(block_type, data, indent)
        if rendered is not None:
            parts.append(rendered)
        prev_type = block_type

    text = "\n".join(parts)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


# ── Helpers ────────────────────────────────────────────────────────────────

_LIST_TYPES = frozenset({"bulleted_list_item", "numbered_list_item", "to_do"})


def _is_same_list_group(prev: str, cur: str) -> bool:
    """True when two adjacent blocks should NOT get a blank line between them."""
    return prev == cur and cur in _LIST_TYPES


def _indent_str(indent: int) -> str:
    return " " * indent


def _get_rich_text(data: dict[str, Any]) -> list[Any]:
    return cast("list[Any]", data.get("rich_text", []))


def _get_children(data: dict[str, Any]) -> list[Any]:
    return cast("list[Any]", data.get("children", []))


# ── Block dispatcher ──────────────────────────────────────────────────────

_BlockRenderer = Callable[[dict[str, Any], int], str]


def _render_block(
    block_type: str,
    data: dict[str, Any],
    indent: int,
) -> str | None:
    """Dispatch to the correct renderer for *block_type*."""
    renderer = _RENDERERS.get(block_type)
    if renderer is not None:
        return renderer(data, indent)
    return None


# ── Block renderers ───────────────────────────────────────────────────────


def _render_paragraph(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    return prefix + render_rich_text(_get_rich_text(data))


def _render_heading_1(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    return f"{prefix}# {render_rich_text(_get_rich_text(data))}"


def _render_heading_2(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    return f"{prefix}## {render_rich_text(_get_rich_text(data))}"


def _render_heading_3(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    return f"{prefix}### {render_rich_text(_get_rich_text(data))}"


def _render_bulleted_list_item(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    text = render_rich_text(_get_rich_text(data))
    result = f"{prefix}- {text}"
    children = _get_children(data)
    if children:
        result += "\n" + render_blocks(children, indent=indent + 4).rstrip("\n")
    return result


def _render_numbered_list_item(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    text = render_rich_text(_get_rich_text(data))
    result = f"{prefix}1. {text}"
    children = _get_children(data)
    if children:
        result += "\n" + render_blocks(children, indent=indent + 4).rstrip("\n")
    return result


def _render_to_do(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    checked: bool = data.get("checked", False)
    marker = "[x]" if checked else "[ ]"
    text = render_rich_text(_get_rich_text(data))
    result = f"{prefix}- {marker} {text}"
    children = _get_children(data)
    if children:
        result += "\n" + render_blocks(children, indent=indent + 4).rstrip("\n")
    return result


def _render_code(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    language: str = data.get("language", "plain text")
    # Don't emit a language tag for plain text
    lang_tag = "" if language == "plain text" else language
    content = render_rich_text(_get_rich_text(data))
    return f"{prefix}```{lang_tag}\n{prefix}{content}\n{prefix}```"


def _render_quote(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    text = render_rich_text(_get_rich_text(data))
    lines = text.splitlines() if text else [""]
    result = "\n".join(f"{prefix}> {line}" for line in lines)
    children = _get_children(data)
    if children:
        child_md = render_blocks(children, indent=0).rstrip("\n")
        for line in child_md.splitlines():
            result += f"\n{prefix}> {line}"
    return result


def _render_callout(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    icon_obj = data.get("icon", {})
    emoji: str = icon_obj.get("emoji", "") if isinstance(icon_obj, dict) else ""
    text = render_rich_text(_get_rich_text(data))
    body = f"{emoji} {text}".strip() if emoji else text
    return f"{prefix}<aside>\n{prefix}{body}\n{prefix}</aside>"


def _render_toggle(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    title = render_rich_text(_get_rich_text(data))
    children = _get_children(data)
    body = ""
    if children:
        child: dict[str, Any] = cast("dict[str, Any]", children[0])
        child_type: str = child.get("type", "")
        child_data: dict[str, Any] = child.get(child_type, {})
        body = render_rich_text(_get_rich_text(child_data))
    return f"{prefix}<details><summary>{title}</summary>{body}</details>"


def _render_divider(_data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    return f"{prefix}---"


def _render_table(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    rows: list[dict[str, Any]] = data.get("children", [])
    if not rows:
        return ""
    has_header: bool = data.get("has_column_header", False)

    lines: list[str] = []
    for i, row in enumerate(rows):
        cells: list[list[Any]] = row.get("table_row", {}).get("cells", [])
        cell_strs = [render_rich_text(cell) for cell in cells]
        line = f"{prefix}| " + " | ".join(cell_strs) + " |"
        lines.append(line)
        if i == 0 and has_header:
            sep = f"{prefix}|" + "|".join(" --- " for _ in cells) + "|"
            lines.append(sep)
    return "\n".join(lines)


def _render_image(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    external: dict[str, str] = data.get("external", {})
    url: str = external.get("url", "")
    caption_items: list[Any] = data.get("caption", [])
    alt = render_rich_text(caption_items) if caption_items else ""
    return f"{prefix}![{alt}]({url})"


def _render_equation(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    expression: str = data.get("expression", "")
    return f"{prefix}$$\n{prefix}{expression}\n{prefix}$$"


def _render_bookmark(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    url: str = data.get("url", "")
    return f"{prefix}[{url}]({url})"


def _render_embed(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    url: str = data.get("url", "")
    return f"{prefix}[{url}]({url})"


def _render_video(data: dict[str, Any], indent: int) -> str:
    prefix = _indent_str(indent)
    external: dict[str, str] = data.get("external", {})
    url: str = external.get("url", "")
    return f"{prefix}![video]({url})"


# ── Renderer registry ─────────────────────────────────────────────────────

_RENDERERS: dict[str, _BlockRenderer] = {
    "paragraph": _render_paragraph,
    "heading_1": _render_heading_1,
    "heading_2": _render_heading_2,
    "heading_3": _render_heading_3,
    "bulleted_list_item": _render_bulleted_list_item,
    "numbered_list_item": _render_numbered_list_item,
    "to_do": _render_to_do,
    "code": _render_code,
    "quote": _render_quote,
    "callout": _render_callout,
    "toggle": _render_toggle,
    "divider": _render_divider,
    "table": _render_table,
    "image": _render_image,
    "equation": _render_equation,
    "bookmark": _render_bookmark,
    "embed": _render_embed,
    "video": _render_video,
}
