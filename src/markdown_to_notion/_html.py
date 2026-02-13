"""Parse Notion-specific HTML patterns into Notion API blocks and rich-text.

Handles HTML elements that appear in Notion markdown exports and Notion's
enhanced markdown format:

**Block-level:**
- ``<aside>`` / ``<callout>`` -- callout blocks
- ``<details><summary>`` -- toggle blocks

**Inline:**
- ``<br>`` / ``<br/>`` -- line breaks
- ``<span underline="true">`` -- underline annotation
- ``<span color="...">`` -- color annotation
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_to_notion._types import NotionBlock, RichText

# ── Regex patterns ─────────────────────────────────────────────────────────

# Block: <aside>...</aside> (Notion export callouts)
_ASIDE_RE = re.compile(
    r"<aside>\s*(.*?)\s*</aside>",
    re.DOTALL,
)

# Block: <callout icon="emoji" color="color">...</callout> (Notion enhanced MD)
# May be wrapped in <div data-notion="callout"> by preprocessor
_CALLOUT_RE = re.compile(
    r'(?:<div data-notion="callout">)?'
    r'<callout\s*(?:icon=["\']([^"\']*)["\'])?\s*(?:color=["\']([^"\']*)["\'])?\s*>'
    r"(.*?)"
    r"</callout>"
    r"(?:</div>)?",
    re.DOTALL,
)

# Block: <details><summary>title</summary>content</details>
_DETAILS_RE = re.compile(
    r"<details>\s*<summary>(.*?)</summary>(.*?)</details>",
    re.DOTALL,
)

# Inline: <br> or <br/>
_BR_RE = re.compile(r"<br\s*/?>")

# Inline: <span underline="true"> or <span color="...">
_SPAN_OPEN_RE = re.compile(
    r"<span\s+"
    r'(?:underline=["\']true["\']|color=["\']([^"\']+)["\'])'
    r"\s*>",
)

_SPAN_CLOSE_RE = re.compile(r"</span>")

# Emoji detection: first character(s) of callout content
_EMOJI_RE = re.compile(
    r"^([\U0001f300-\U0001faff\U00002702-\U000027b0\U0000fe0f"
    r"\U0001f900-\U0001f9ff\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff"
    r"\U00002600-\U000026ff\U00002700-\U000027bf\u200d]+)\s*",
)


# ── Inline HTML result ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class InlineHTMLResult:
    """Result of parsing an inline HTML tag."""

    is_br: bool = False
    is_span_open: bool = False
    is_span_close: bool = False
    underline: bool = False
    color: str = ""


# ── Block-level HTML parsing ──────────────────────────────────────────────


def _plain(content: str) -> RichText:
    return {"type": "text", "text": {"content": content}}


def parse_block_html(raw: str) -> list[NotionBlock] | None:
    """Try to parse a block HTML string as a Notion-specific block.

    Returns a list of blocks if the HTML matches a known pattern,
    or ``None`` if unrecognized (caller should fall back to paragraph).
    """
    stripped = raw.strip()

    # ── <aside>...</aside> → callout ──────────────────────────────────
    m = _ASIDE_RE.match(stripped)
    if m:
        return _build_callout_from_content(m.group(1).strip())

    # ── <callout ...>...</callout> → callout ──────────────────────────
    m = _CALLOUT_RE.match(stripped)
    if m:
        icon = (m.group(1) or "").strip()
        color = (m.group(2) or "").strip()
        content = (m.group(3) or "").strip()
        return _build_callout(content, icon=icon, color=color)

    # ── <details><summary>...</summary>...</details> → toggle ─────────
    m = _DETAILS_RE.match(stripped)
    if m:
        title = m.group(1).strip()
        body = m.group(2).strip()
        return _build_toggle(title, body)

    return None


def _build_callout_from_content(content: str) -> list[NotionBlock]:
    """Build a callout from raw aside content, extracting a leading emoji."""
    icon = ""
    text = content

    emoji_match = _EMOJI_RE.match(content)
    if emoji_match:
        icon = emoji_match.group(1)
        text = content[emoji_match.end() :].strip()

    return _build_callout(text, icon=icon, color="")


def _build_callout(
    content: str,
    *,
    icon: str,
    color: str,
) -> list[NotionBlock]:
    """Build a Notion callout block."""
    rich_text: list[RichText] = [_plain(content)] if content else []

    if icon and color:
        return [
            {
                "type": "callout",
                "callout": {"rich_text": rich_text, "icon": {"emoji": icon}, "color": color},
            }
        ]
    if icon:
        return [{"type": "callout", "callout": {"rich_text": rich_text, "icon": {"emoji": icon}}}]
    if color:
        return [{"type": "callout", "callout": {"rich_text": rich_text, "color": color}}]
    return [{"type": "callout", "callout": {"rich_text": rich_text}}]


def _build_toggle(title: str, body: str) -> list[NotionBlock]:
    """Build a Notion toggle block from details/summary HTML."""
    rich_text: list[RichText] = [_plain(title)] if title else []
    children: list[NotionBlock] = []

    if body:
        children.append({"type": "paragraph", "paragraph": {"rich_text": [_plain(body)]}})

    if children:
        return [{"type": "toggle", "toggle": {"rich_text": rich_text, "children": children}}]
    return [{"type": "toggle", "toggle": {"rich_text": rich_text}}]


# ── Inline HTML parsing ───────────────────────────────────────────────────


def parse_inline_html(raw: str) -> InlineHTMLResult | None:
    """Try to parse an inline HTML tag as a Notion-specific element.

    Returns an ``InlineHTMLResult`` if recognized, or ``None`` if unrecognized.
    """
    stripped = raw.strip()

    # ── <br> / <br/> ─────────────────────────────────────────────────
    if _BR_RE.fullmatch(stripped):
        return InlineHTMLResult(is_br=True)

    # ── <span underline="true"> or <span color="..."> ────────────────
    m = _SPAN_OPEN_RE.fullmatch(stripped)
    if m:
        color_val = m.group(1) or ""
        if color_val:
            return InlineHTMLResult(is_span_open=True, color=color_val)
        # No color group means it matched underline="true"
        return InlineHTMLResult(is_span_open=True, underline=True)

    # ── </span> ──────────────────────────────────────────────────────
    if _SPAN_CLOSE_RE.fullmatch(stripped):
        return InlineHTMLResult(is_span_close=True)

    return None


# ── Pre-processing ────────────────────────────────────────────────────────

# Matches <aside>...</aside> that may span multiple lines
_ASIDE_BLOCK_RE = re.compile(
    r"<aside>(.*?)</aside>",
    re.DOTALL,
)

# Matches <callout ...>...</callout> that may span multiple lines
_CALLOUT_BLOCK_RE = re.compile(
    r"(<callout\b[^>]*>.*?</callout>)",
    re.DOTALL,
)

# Matches <details>...</details> that may span multiple lines
_DETAILS_BLOCK_RE = re.compile(
    r"(<details>.*?</details>)",
    re.DOTALL,
)


def preprocess_notion_html(markdown: str) -> str:
    """Normalize Notion-specific HTML blocks so mistune keeps them as single tokens.

    Ensures blank lines surround each block and collapses internal newlines
    so mistune treats the entire tag as one ``block_html`` token.

    For non-standard tags like ``<callout>``, wraps the content in a
    ``<div>`` with a ``data-notion`` attribute so mistune treats it as a
    block-level HTML element, then ``parse_block_html`` unwraps it.
    """
    # Collapse standard HTML block tags onto a single line
    result = _ASIDE_BLOCK_RE.sub(_collapse_html_block, markdown)
    result = _DETAILS_BLOCK_RE.sub(_collapse_html_block, result)

    # Wrap <callout> in a <div data-notion="callout"> so mistune sees it as block HTML
    return _CALLOUT_BLOCK_RE.sub(_wrap_callout_block, result)


def _collapse_html_block(m: re.Match[str]) -> str:
    """Collapse a multi-line HTML block to one line with blank-line padding."""
    tag = " ".join(m.group(0).split())
    return f"\n\n{tag}\n\n"


def _wrap_callout_block(m: re.Match[str]) -> str:
    """Wrap a <callout> tag in <div> so mistune treats it as block HTML."""
    tag = " ".join(m.group(0).split())
    return f'\n\n<div data-notion="callout">{tag}</div>\n\n'
