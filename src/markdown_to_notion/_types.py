"""TypedDict definitions for Notion API block and rich-text objects.

Every public type is a ``TypedDict`` so callers get full IDE autocomplete and
type-checking.  The structures match what the Notion API expects when
**creating** blocks (i.e. only the fields you send, not the read-only fields
that come back in responses).
"""

from __future__ import annotations

from typing import Literal, TypedDict, Union

from typing_extensions import NotRequired

# ── Rich Text ──────────────────────────────────────────────────────────────


class LinkObject(TypedDict):
    """A hyperlink target."""

    url: str


class TextContent(TypedDict):
    """The ``text`` payload inside a rich-text item."""

    content: str
    link: NotRequired[LinkObject | None]


class RichTextAnnotations(TypedDict, total=False):
    """Styling annotations applied to a rich-text span."""

    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: str


class RichTextText(TypedDict):
    """A ``"text"``-type rich-text item."""

    type: Literal["text"]
    text: TextContent
    annotations: NotRequired[RichTextAnnotations]


class EquationContent(TypedDict):
    """The ``equation`` payload inside a rich-text item."""

    expression: str


class RichTextEquation(TypedDict):
    """An ``"equation"``-type rich-text item (inline math)."""

    type: Literal["equation"]
    equation: EquationContent
    annotations: NotRequired[RichTextAnnotations]


RichText = Union[RichTextText, RichTextEquation]
"""Union of all rich-text item variants."""

# ── Paragraph ──────────────────────────────────────────────────────────────


class ParagraphData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class ParagraphBlock(TypedDict):
    type: Literal["paragraph"]
    paragraph: ParagraphData


# ── Headings ───────────────────────────────────────────────────────────────


class HeadingData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    is_toggleable: NotRequired[bool]


class HeadingOneBlock(TypedDict):
    type: Literal["heading_1"]
    heading_1: HeadingData


class HeadingTwoBlock(TypedDict):
    type: Literal["heading_2"]
    heading_2: HeadingData


class HeadingThreeBlock(TypedDict):
    type: Literal["heading_3"]
    heading_3: HeadingData


# ── List items ─────────────────────────────────────────────────────────────


class BulletedListItemData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class BulletedListItemBlock(TypedDict):
    type: Literal["bulleted_list_item"]
    bulleted_list_item: BulletedListItemData


class NumberedListItemData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class NumberedListItemBlock(TypedDict):
    type: Literal["numbered_list_item"]
    numbered_list_item: NumberedListItemData


# ── To-do ──────────────────────────────────────────────────────────────────


class ToDoData(TypedDict):
    rich_text: list[RichText]
    checked: bool
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class ToDoBlock(TypedDict):
    type: Literal["to_do"]
    to_do: ToDoData


# ── Code ───────────────────────────────────────────────────────────────────


class CodeData(TypedDict):
    rich_text: list[RichText]
    language: str
    caption: NotRequired[list[RichText]]


class CodeBlock(TypedDict):
    type: Literal["code"]
    code: CodeData


# ── Quote ──────────────────────────────────────────────────────────────────


class QuoteData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class QuoteBlock(TypedDict):
    type: Literal["quote"]
    quote: QuoteData


# ── Callout ────────────────────────────────────────────────────────────────


class CalloutIcon(TypedDict, total=False):
    emoji: str


class CalloutData(TypedDict):
    rich_text: list[RichText]
    icon: NotRequired[CalloutIcon]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class CalloutBlock(TypedDict):
    type: Literal["callout"]
    callout: CalloutData


# ── Toggle ─────────────────────────────────────────────────────────────────


class ToggleData(TypedDict):
    rich_text: list[RichText]
    color: NotRequired[str]
    children: NotRequired[list[NotionBlock]]


class ToggleBlock(TypedDict):
    type: Literal["toggle"]
    toggle: ToggleData


# ── Divider ────────────────────────────────────────────────────────────────


class _EmptyDict(TypedDict):
    pass


class DividerBlock(TypedDict):
    type: Literal["divider"]
    divider: _EmptyDict


# ── Table ──────────────────────────────────────────────────────────────────


class TableRowData(TypedDict):
    cells: list[list[RichText]]


class TableRowBlock(TypedDict):
    type: Literal["table_row"]
    table_row: TableRowData


class TableData(TypedDict):
    table_width: int
    has_column_header: bool
    has_row_header: bool
    children: list[TableRowBlock]


class TableBlock(TypedDict):
    type: Literal["table"]
    table: TableData


# ── Image ──────────────────────────────────────────────────────────────────


class ExternalFile(TypedDict):
    url: str


class ImageData(TypedDict):
    type: Literal["external"]
    external: ExternalFile
    caption: NotRequired[list[RichText]]


class ImageBlock(TypedDict):
    type: Literal["image"]
    image: ImageData


# ── Equation (block-level) ─────────────────────────────────────────────────


class EquationBlockData(TypedDict):
    expression: str


class EquationBlock(TypedDict):
    type: Literal["equation"]
    equation: EquationBlockData


# ── Bookmark ───────────────────────────────────────────────────────────────


class BookmarkData(TypedDict):
    url: str
    caption: NotRequired[list[RichText]]


class BookmarkBlock(TypedDict):
    type: Literal["bookmark"]
    bookmark: BookmarkData


# ── Embed ──────────────────────────────────────────────────────────────────


class EmbedData(TypedDict):
    url: str


class EmbedBlock(TypedDict):
    type: Literal["embed"]
    embed: EmbedData


# ── Video ──────────────────────────────────────────────────────────────────


class VideoData(TypedDict):
    type: Literal["external"]
    external: ExternalFile


class VideoBlock(TypedDict):
    type: Literal["video"]
    video: VideoData


# ── Union of all blocks ───────────────────────────────────────────────────

NotionBlock = Union[
    ParagraphBlock,
    HeadingOneBlock,
    HeadingTwoBlock,
    HeadingThreeBlock,
    BulletedListItemBlock,
    NumberedListItemBlock,
    ToDoBlock,
    CodeBlock,
    QuoteBlock,
    CalloutBlock,
    ToggleBlock,
    DividerBlock,
    TableBlock,
    TableRowBlock,
    ImageBlock,
    EquationBlock,
    BookmarkBlock,
    EmbedBlock,
    VideoBlock,
]
"""Union of every Notion block type this library can produce."""


# ── Internal: mistune AST token types (not part of the public API) ─────────


class _TokenAttrs(TypedDict, total=False):
    """Fields that appear in ``attrs`` on various mistune token types."""

    level: int
    info: str
    ordered: bool
    depth: int
    checked: bool
    start: int
    url: str
    alt: str
    src: str
    title: str | None
    align: str | None
    head: bool


class _Token(TypedDict, total=False):
    """Structural representation of a single mistune AST token.

    ``total=False`` because every token type uses a different subset of keys.
    """

    type: str
    raw: str
    children: list[_Token]
    attrs: _TokenAttrs
    style: str
    marker: str
    tight: bool
    bullet: str
