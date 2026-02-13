"""Convert Markdown to Notion API block objects.

.. code-block:: python

    from notion_markdown import convert

    blocks = convert("# Hello\\n\\nSome **bold** text.")
    # → list of Notion API block dicts, ready for notion-client

The return value can be passed directly to ``notion-client``::

    from notion_client import Client

    notion = Client(auth="secret_…")
    notion.pages.create(
        parent={"page_id": "…"},
        properties={"title": [{"text": {"content": "My Page"}}]},
        children=blocks,
    )
"""

from notion_markdown._parser import parse
from notion_markdown._types import (
    BookmarkBlock,
    BookmarkData,
    BulletedListItemBlock,
    BulletedListItemData,
    CalloutBlock,
    CalloutData,
    CodeBlock,
    CodeData,
    DividerBlock,
    EmbedBlock,
    EmbedData,
    EquationBlock,
    EquationBlockData,
    EquationContent,
    ExternalFile,
    HeadingData,
    HeadingOneBlock,
    HeadingThreeBlock,
    HeadingTwoBlock,
    ImageBlock,
    ImageData,
    LinkObject,
    NotionBlock,
    NumberedListItemBlock,
    NumberedListItemData,
    ParagraphBlock,
    ParagraphData,
    QuoteBlock,
    QuoteData,
    RichText,
    RichTextAnnotations,
    RichTextEquation,
    RichTextText,
    TableBlock,
    TableData,
    TableRowBlock,
    TableRowData,
    TextContent,
    ToDoBlock,
    ToDoData,
    ToggleBlock,
    ToggleData,
    VideoBlock,
    VideoData,
)

__version__ = "0.1.0"


def convert(markdown: str) -> list[NotionBlock]:
    """Convert a Markdown string to a list of Notion API block objects.

    Parameters
    ----------
    markdown:
        The Markdown source text to convert.

    Returns
    -------
    list[NotionBlock]
        A list of ``TypedDict`` block objects matching the Notion API schema.
        Pass them to ``notion-client`` as ``children`` in
        ``pages.create()`` or ``blocks.children.append()``.

    Examples
    --------
    >>> from notion_markdown import convert
    >>> blocks = convert("# Title\\n\\nHello **world**!")
    >>> blocks[0]["type"]
    'heading_1'
    """
    return parse(markdown)


__all__ = [
    "BookmarkBlock",
    "BookmarkData",
    "BulletedListItemBlock",
    "BulletedListItemData",
    "CalloutBlock",
    "CalloutData",
    "CodeBlock",
    "CodeData",
    "DividerBlock",
    "EmbedBlock",
    "EmbedData",
    "EquationBlock",
    "EquationBlockData",
    "EquationContent",
    "ExternalFile",
    "HeadingData",
    "HeadingOneBlock",
    "HeadingThreeBlock",
    "HeadingTwoBlock",
    "ImageBlock",
    "ImageData",
    "LinkObject",
    "NotionBlock",
    "NumberedListItemBlock",
    "NumberedListItemData",
    "ParagraphBlock",
    "ParagraphData",
    "QuoteBlock",
    "QuoteData",
    "RichText",
    "RichTextAnnotations",
    "RichTextEquation",
    "RichTextText",
    "TableBlock",
    "TableData",
    "TableRowBlock",
    "TableRowData",
    "TextContent",
    "ToDoBlock",
    "ToDoData",
    "ToggleBlock",
    "ToggleData",
    "VideoBlock",
    "VideoData",
    "__version__",
    "convert",
]
