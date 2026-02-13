"""Render Notion ``rich_text`` items back to inline Markdown.

This is the inverse of :mod:`notion_markdown._inline`.  Each
:class:`~notion_markdown._types.RichText` item becomes a Markdown string
with the appropriate formatting markers applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from notion_markdown._types import RichText, RichTextAnnotations


def render_rich_text(items: list[RichText]) -> str:
    """Convert a list of Notion rich-text items to a Markdown string.

    Parameters
    ----------
    items:
        Notion rich-text items (``RichTextText`` or ``RichTextEquation``).

    Returns
    -------
    str
        The Markdown representation of the combined rich-text.
    """
    return "".join(_render_one(item) for item in items)


def _render_one(item: RichText) -> str:
    """Render a single rich-text item to Markdown."""
    # Cast to Any to work around TypedDict union access limitations
    d: dict[str, Any] = cast("dict[str, Any]", item)
    item_type: str = d.get("type", "text")

    if item_type == "equation":
        eq: dict[str, str] = d.get("equation", {})
        expr: str = eq.get("expression", "")
        return f"${expr}$"

    # Plain text item
    text_obj: dict[str, Any] = d.get("text", {})
    content: str = text_obj.get("content", "")

    if not content:
        return ""

    annotations: RichTextAnnotations = d.get("annotations", {})
    link_obj = text_obj.get("link")
    link_url: str = ""
    if isinstance(link_obj, dict):
        link_url = link_obj.get("url", "")

    return _apply_formatting(content, annotations, link_url)


def _apply_formatting(
    content: str,
    annotations: RichTextAnnotations,
    link_url: str,
) -> str:
    """Wrap *content* in the appropriate Markdown markers."""
    result = content

    # Code must be applied first and is mutually exclusive with other markers
    if annotations.get("code"):
        result = f"`{result}`"
        if link_url:
            result = f"[{result}]({link_url})"
        return result

    # Underline → HTML span (no standard MD equivalent)
    if annotations.get("underline"):
        result = f'<span underline="true">{result}</span>'

    # Color → HTML span
    color: str = annotations.get("color", "")
    if color:
        result = f'<span color="{color}">{result}</span>'

    # Strikethrough wraps
    if annotations.get("strikethrough"):
        result = f"~~{result}~~"

    # Bold + italic combine as ***…***
    bold = annotations.get("bold", False)
    italic = annotations.get("italic", False)
    if bold and italic:
        result = f"***{result}***"
    elif bold:
        result = f"**{result}**"
    elif italic:
        result = f"*{result}*"

    # Link wraps everything
    if link_url:
        result = f"[{result}]({link_url})"

    return result
