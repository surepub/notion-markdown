"""Convert mistune inline AST tokens to Notion ``rich_text`` objects.

The core challenge is that Markdown inline formatting is *nested* (e.g.
``**bold _and italic_**``) while Notion rich-text is *flat* — each span
carries its own annotations dict.  We solve this by recursively walking the
mistune inline tree and accumulating a ``_Style`` dataclass as we descend.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_to_notion._types import (
        RichText,
        RichTextAnnotations,
        RichTextEquation,
        RichTextText,
        _Token,
    )


# ── Style accumulator ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _Style:
    """Immutable bag of inline formatting state accumulated while walking tokens."""

    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False


_DEFAULT_STYLE = _Style()

# Mapping from mistune container token type → _Style field name
_CONTAINER_FIELD: dict[str, str] = {
    "strong": "bold",
    "emphasis": "italic",
    "strikethrough": "strikethrough",
    "mark": "underline",
    "insert": "underline",
}

_CONTAINER_TYPES = frozenset(_CONTAINER_FIELD)


# ── Helpers ────────────────────────────────────────────────────────────────


def _tok_raw(tok: _Token) -> str:
    """Get the ``raw`` text payload from a leaf token."""
    r = tok.get("raw")
    if isinstance(r, str):
        return r
    t = tok.get("text")  # some older tokens carry 'text'
    if isinstance(t, str):
        return t
    c = tok.get("children")
    if isinstance(c, str):
        return c
    return ""


def _tok_children(tok: _Token) -> list[_Token]:
    """Get the ``children`` list from a token, defaulting to ``[]``."""
    c = tok.get("children")
    if c is None:
        return []
    return c


def _tok_type(tok: _Token) -> str:
    return tok.get("type", "")


def _to_annotations(style: _Style) -> RichTextAnnotations:
    """Convert a ``_Style`` to a ``RichTextAnnotations`` dict (omitting falsy keys)."""
    result: RichTextAnnotations = {}
    if style.bold:
        result["bold"] = True
    if style.italic:
        result["italic"] = True
    if style.strikethrough:
        result["strikethrough"] = True
    if style.underline:
        result["underline"] = True
    if style.code:
        result["code"] = True
    return result


def _make_text(
    content: str,
    style: _Style,
    link_url: str | None = None,
) -> RichTextText:
    """Build a Notion ``RichTextText`` item."""
    if link_url is not None:
        text_obj: RichTextText = {
            "type": "text",
            "text": {"content": content, "link": {"url": link_url}},
        }
    else:
        text_obj = {"type": "text", "text": {"content": content}}

    annotations = _to_annotations(style)
    if annotations:
        text_obj["annotations"] = annotations
    return text_obj


def _make_equation(expression: str) -> RichTextEquation:
    """Build an inline equation rich-text item."""
    return {"type": "equation", "equation": {"expression": expression}}


# ── Public entry point ─────────────────────────────────────────────────────


def parse_inline(
    children: list[_Token],
    *,
    _style: _Style = _DEFAULT_STYLE,
    _link_url: str | None = None,
) -> list[RichText]:
    """Convert a list of mistune inline AST tokens to Notion rich-text items.

    Parameters
    ----------
    children:
        The ``children`` list from a mistune block token (paragraph, heading,
        etc.) after AST-mode inline parsing.

    Returns
    -------
    list[RichText]
        Flat list of Notion rich-text items ready for the API.
    """
    result: list[RichText] = []

    for token in children:
        ttype = _tok_type(token)

        # ── Leaf: plain text ───────────────────────────────────────────
        if ttype == "text":
            raw = _tok_raw(token)
            if raw:
                result.append(_make_text(raw, _style, _link_url))

        # ── Container: bold / italic / strikethrough / etc. ────────────
        elif ttype in _CONTAINER_TYPES:
            field = _CONTAINER_FIELD[ttype]
            child_style = replace(_style, **{field: True})
            result.extend(
                parse_inline(_tok_children(token), _style=child_style, _link_url=_link_url),
            )

        # ── Leaf: inline code ──────────────────────────────────────────
        elif ttype == "codespan":
            raw = _tok_raw(token)
            result.append(_make_text(raw, replace(_style, code=True), _link_url))

        # ── Container: link ────────────────────────────────────────────
        elif ttype == "link":
            attrs = tok.get("attrs") if (tok := token) else None
            url = ""
            if isinstance(attrs, dict):
                u = attrs.get("url")
                if isinstance(u, str):
                    url = u
            result.extend(
                parse_inline(_tok_children(token), _style=_style, _link_url=url),
            )

        # ── Inline image (inside a paragraph with other text) ─────────
        elif ttype == "image":
            attrs = token.get("attrs")
            url = ""
            alt = ""
            if isinstance(attrs, dict):
                u = attrs.get("url")
                if isinstance(u, str):
                    url = u
                a = attrs.get("alt")
                if isinstance(a, str):
                    alt = a
            img_children = _tok_children(token)
            if img_children:
                result.extend(parse_inline(img_children, _style=_style, _link_url=url))
            elif alt:
                result.append(_make_text(alt, _style, url))

        # ── Line breaks (soft or hard) → newline character ─────────────
        elif ttype in ("softbreak", "linebreak"):
            result.append(_make_text("\n", _style, _link_url))

        # ── Inline math: $ ... $ ───────────────────────────────────────
        elif ttype in ("inline_math", "math"):
            raw = _tok_raw(token)
            if raw:
                result.append(_make_equation(raw))

        # ── Raw inline HTML — pass through as plain text ───────────────
        elif ttype in ("inline_html", "html"):
            raw = _tok_raw(token)
            if raw:
                result.append(_make_text(raw, _style, _link_url))

    return result
