"""Tests for inline Markdown → Notion rich_text conversion."""

from __future__ import annotations

import mistune

from markdown_to_notion._inline import (
    _make_equation,
    _make_text,
    _Style,
    _to_annotations,
    _tok_children,
    _tok_raw,
    _tok_type,
    parse_inline,
)

# Helper: parse inline markdown by extracting the children of a paragraph AST node.
_md = mistune.create_markdown(renderer="ast", plugins=["strikethrough", "math"])


def _inline(text: str) -> list[dict]:
    """Parse *inline* markdown and return the inline tokens."""
    tokens = _md(text)
    assert tokens, f"No tokens from: {text!r}"
    return tokens[0].get("children", [])


# ── Token accessor helpers ─────────────────────────────────────────────────


class TestTokRaw:
    def test_raw_field(self) -> None:
        assert _tok_raw({"type": "text", "raw": "hello"}) == "hello"

    def test_text_field_fallback(self) -> None:
        assert _tok_raw({"type": "x", "text": "fallback"}) == "fallback"

    def test_children_string_fallback(self) -> None:
        assert _tok_raw({"type": "x", "children": "stringchildren"}) == "stringchildren"

    def test_empty_fallback(self) -> None:
        assert _tok_raw({"type": "x"}) == ""

    def test_non_string_raw(self) -> None:
        assert _tok_raw({"type": "x", "raw": 123}) == ""  # type: ignore[typeddict-item]


class TestTokChildren:
    def test_returns_children_list(self) -> None:
        tok = {"type": "strong", "children": [{"type": "text", "raw": "a"}]}
        assert len(_tok_children(tok)) == 1

    def test_returns_empty_when_none(self) -> None:
        assert _tok_children({"type": "text", "raw": "x"}) == []


class TestTokType:
    def test_returns_type(self) -> None:
        assert _tok_type({"type": "text"}) == "text"

    def test_returns_empty_for_missing(self) -> None:
        assert _tok_type({}) == ""


# ── Style and annotation helpers ───────────────────────────────────────────


class TestStyle:
    def test_default_style(self) -> None:
        s = _Style()
        assert not s.bold
        assert not s.italic
        assert not s.strikethrough
        assert not s.underline
        assert not s.code

    def test_to_annotations_empty(self) -> None:
        assert _to_annotations(_Style()) == {}

    def test_to_annotations_bold(self) -> None:
        assert _to_annotations(_Style(bold=True)) == {"bold": True}

    def test_to_annotations_all(self) -> None:
        s = _Style(bold=True, italic=True, strikethrough=True, underline=True, code=True)
        a = _to_annotations(s)
        assert a["bold"] is True
        assert a["italic"] is True
        assert a["strikethrough"] is True
        assert a["underline"] is True
        assert a["code"] is True


class TestMakeText:
    def test_plain(self) -> None:
        item = _make_text("hello", _Style())
        assert item["type"] == "text"
        assert item["text"]["content"] == "hello"
        assert "annotations" not in item
        assert "link" not in item["text"]

    def test_with_link(self) -> None:
        item = _make_text("click", _Style(), link_url="https://a.com")
        assert item["text"]["link"] == {"url": "https://a.com"}

    def test_with_annotations(self) -> None:
        item = _make_text("bold", _Style(bold=True))
        assert item["annotations"] == {"bold": True}


class TestMakeEquation:
    def test_simple(self) -> None:
        item = _make_equation("x^2")
        assert item["type"] == "equation"
        assert item["equation"]["expression"] == "x^2"


# ── parse_inline tests ────────────────────────────────────────────────────


class TestPlainText:
    def test_simple(self) -> None:
        items = parse_inline(_inline("hello"))
        assert len(items) == 1
        assert items[0]["type"] == "text"
        assert items[0]["text"]["content"] == "hello"
        assert "annotations" not in items[0]

    def test_multiline(self) -> None:
        items = parse_inline(_inline("hello\nworld"))
        contents = "".join(it["text"]["content"] for it in items)
        assert "hello" in contents
        assert "world" in contents


class TestBold:
    def test_double_asterisk(self) -> None:
        items = parse_inline(_inline("**bold**"))
        assert len(items) == 1
        assert items[0]["text"]["content"] == "bold"
        assert items[0]["annotations"]["bold"] is True

    def test_double_underscore(self) -> None:
        items = parse_inline(_inline("__bold__"))
        assert len(items) == 1
        assert items[0]["annotations"]["bold"] is True

    def test_bold_in_sentence(self) -> None:
        items = parse_inline(_inline("some **bold** text"))
        assert len(items) == 3
        assert "annotations" not in items[0]
        assert items[1]["annotations"]["bold"] is True
        assert items[2]["text"]["content"] == " text"


class TestItalic:
    def test_single_asterisk(self) -> None:
        items = parse_inline(_inline("*italic*"))
        assert items[0]["annotations"]["italic"] is True

    def test_single_underscore(self) -> None:
        items = parse_inline(_inline("_italic_"))
        assert items[0]["annotations"]["italic"] is True


class TestStrikethrough:
    def test_strikethrough(self) -> None:
        items = parse_inline(_inline("~~deleted~~"))
        assert items[0]["annotations"]["strikethrough"] is True


class TestInlineCode:
    def test_backtick(self) -> None:
        items = parse_inline(_inline("`code`"))
        assert items[0]["text"]["content"] == "code"
        assert items[0]["annotations"]["code"] is True

    def test_code_in_sentence(self) -> None:
        items = parse_inline(_inline("use `fmt.Println` here"))
        assert items[1]["text"]["content"] == "fmt.Println"
        assert items[1]["annotations"]["code"] is True


class TestLinks:
    def test_simple_link(self) -> None:
        items = parse_inline(_inline("[click](https://example.com)"))
        assert items[0]["text"]["content"] == "click"
        assert items[0]["text"]["link"]["url"] == "https://example.com"

    def test_bold_link(self) -> None:
        items = parse_inline(_inline("[**bold link**](https://example.com)"))
        assert items[0]["text"]["content"] == "bold link"
        assert items[0]["text"]["link"]["url"] == "https://example.com"
        assert items[0]["annotations"]["bold"] is True


class TestNestedFormatting:
    def test_bold_and_italic(self) -> None:
        items = parse_inline(_inline("***bold italic***"))
        assert items[0]["annotations"]["bold"] is True
        assert items[0]["annotations"]["italic"] is True

    def test_bold_with_italic_inside(self) -> None:
        items = parse_inline(_inline("**bold and *italic* text**"))
        for item in items:
            assert item["annotations"]["bold"] is True
        italic_items = [it for it in items if it.get("annotations", {}).get("italic")]
        assert len(italic_items) >= 1

    def test_strikethrough_bold(self) -> None:
        items = parse_inline(_inline("~~**bold deleted**~~"))
        assert items[0]["annotations"]["bold"] is True
        assert items[0]["annotations"]["strikethrough"] is True


class TestInlineMath:
    def test_inline_equation(self) -> None:
        items = parse_inline(_inline("$x^2$"))
        assert items[0]["type"] == "equation"
        assert items[0]["equation"]["expression"] == "x^2"

    def test_equation_in_sentence(self) -> None:
        items = parse_inline(_inline("The formula $E=mc^2$ is famous."))
        assert items[1]["type"] == "equation"
        assert items[1]["equation"]["expression"] == "E=mc^2"


class TestInlineImage:
    """Test inline images (image mixed with text in a paragraph)."""

    def test_image_with_alt_and_text(self) -> None:
        # Image within text → treated as inline (not standalone block)
        tokens = _inline("See ![photo](https://img.com/a.png) here")
        items = parse_inline(tokens)
        # Should have text + image-as-link + text
        assert len(items) >= 2
        # The image alt text should appear as a linked text
        img_items = [it for it in items if "img.com" in str(it.get("text", {}).get("link", ""))]
        assert len(img_items) >= 1

    def test_image_with_only_alt_no_children(self) -> None:
        """Direct token construction to test the alt-text-only path."""
        tok: dict = {"type": "image", "attrs": {"url": "http://x.com/a.png", "alt": "pic"}}
        items = parse_inline([tok])
        assert len(items) == 1
        assert items[0]["text"]["content"] == "pic"
        assert items[0]["text"]["link"]["url"] == "http://x.com/a.png"


class TestInlineHTML:
    """Test that raw inline HTML is passed through as plain text."""

    def test_html_tag(self) -> None:
        md_html = mistune.create_markdown(renderer="ast", plugins=[])
        tokens = md_html("text <br> more")
        children = tokens[0].get("children", [])
        items = parse_inline(children)
        full_text = "".join(it["text"]["content"] for it in items if it.get("type") == "text")
        assert "text" in full_text

    def test_unrecognized_html_passthrough(self) -> None:
        """Unrecognized inline HTML passes through as plain text."""
        md_html = mistune.create_markdown(renderer="ast", plugins=[])
        tokens = md_html("text <em>emphasis</em> more")
        children = tokens[0].get("children", [])
        items = parse_inline(children)
        # <em> is unrecognized by our parser → pass through as text
        all_text = "".join(it["text"]["content"] for it in items if it.get("type") == "text")
        assert "text" in all_text


class TestInlineBr:
    """Test <br> and <br/> inline tags produce newlines."""

    def test_br_produces_newline(self) -> None:
        from markdown_to_notion import convert

        blocks = convert("line one<br>line two")
        rt = blocks[0]["paragraph"]["rich_text"]
        contents = [it["text"]["content"] for it in rt if it["type"] == "text"]
        assert "\n" in contents

    def test_br_self_closing_produces_newline(self) -> None:
        from markdown_to_notion import convert

        blocks = convert("before<br/>after")
        rt = blocks[0]["paragraph"]["rich_text"]
        contents = [it["text"]["content"] for it in rt if it["type"] == "text"]
        assert "\n" in contents


class TestInlineUnderline:
    """Test <span underline="true"> produces underline annotation."""

    def test_underline_span(self) -> None:
        from markdown_to_notion import convert

        blocks = convert('normal <span underline="true">underlined</span> more')
        rt = blocks[0]["paragraph"]["rich_text"]
        underlined = [it for it in rt if it.get("annotations", {}).get("underline")]
        assert len(underlined) >= 1
        assert underlined[0]["text"]["content"] == "underlined"

    def test_underline_preserves_other_formatting(self) -> None:
        from markdown_to_notion import convert

        blocks = convert('**bold <span underline="true">both</span> bold**')
        rt = blocks[0]["paragraph"]["rich_text"]
        both = [
            it
            for it in rt
            if it.get("annotations", {}).get("underline") and it.get("annotations", {}).get("bold")
        ]
        assert len(both) >= 1


class TestInlineColor:
    """Test <span color="..."> produces color annotation."""

    def test_color_span(self) -> None:
        from markdown_to_notion import convert

        blocks = convert('text <span color="red">red</span> text')
        rt = blocks[0]["paragraph"]["rich_text"]
        colored = [it for it in rt if it.get("annotations", {}).get("color") == "red"]
        assert len(colored) >= 1
        assert colored[0]["text"]["content"] == "red"

    def test_color_background(self) -> None:
        from markdown_to_notion import convert

        blocks = convert('<span color="blue_bg">highlighted</span>')
        rt = blocks[0]["paragraph"]["rich_text"]
        colored = [it for it in rt if it.get("annotations", {}).get("color") == "blue_bg"]
        assert len(colored) >= 1

    def test_orphan_span_close_ignored(self) -> None:
        """A </span> without a matching open is silently ignored."""
        from markdown_to_notion import convert

        blocks = convert("text</span>more")
        # Should not crash; content produced
        assert len(blocks) >= 1


class TestSpanEdgeCases:
    """Test span processing edge cases for full coverage."""

    def test_nested_color_inside_underline(self) -> None:
        """Nested spans: <span underline><span color="red">text</span></span>."""
        from markdown_to_notion import convert

        md = '<span underline="true"><span color="red">both</span></span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        both = [
            it
            for it in rt
            if it.get("annotations", {}).get("underline")
            and it.get("annotations", {}).get("color") == "red"
        ]
        assert len(both) >= 1

    def test_nested_underline_inside_color(self) -> None:
        """Nested spans: <span color><span underline>text</span></span>."""
        from markdown_to_notion import convert

        md = '<span color="blue"><span underline="true">both</span></span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        both = [
            it
            for it in rt
            if it.get("annotations", {}).get("underline")
            and it.get("annotations", {}).get("color") == "blue"
        ]
        assert len(both) >= 1

    def test_bold_inside_color_span(self) -> None:
        """Bold markdown inside a color span."""
        from markdown_to_notion import convert

        md = '<span color="green">**bold green**</span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        colored_bold = [
            it
            for it in rt
            if it.get("annotations", {}).get("color") == "green"
            and it.get("annotations", {}).get("bold")
        ]
        assert len(colored_bold) >= 1

    def test_codespan_inside_underline_span(self) -> None:
        """Inline code inside an underline span."""
        from markdown_to_notion import convert

        md = '<span underline="true">`code`</span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        code_underline = [
            it
            for it in rt
            if it.get("annotations", {}).get("underline") and it.get("annotations", {}).get("code")
        ]
        assert len(code_underline) >= 1

    def test_linebreak_inside_span(self) -> None:
        """A hard line break inside a span."""
        from markdown_to_notion import convert

        md = '<span color="red">line1  \nline2</span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        newlines = [it for it in rt if it.get("text", {}).get("content") == "\n"]
        assert len(newlines) >= 1

    def test_other_token_inside_span(self) -> None:
        """An inline math token inside a color span."""
        from markdown_to_notion import convert

        md = '<span color="blue">before $x^2$ after</span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        # Should have text and equation items
        types = [it["type"] for it in rt]
        assert "text" in types

    def test_span_with_no_closing_tag(self) -> None:
        """An open span with no closing tag consumes everything."""
        from markdown_to_notion import convert

        md = '<span color="red">no closing tag here'
        blocks = convert(md)
        # Should not crash; content produced with color
        assert len(blocks) >= 1

    def test_empty_inline_html_token(self) -> None:
        """An inline_html token with empty raw is skipped."""
        from markdown_to_notion._inline import _handle_inline_html, _Style

        result = _handle_inline_html(
            {"type": "inline_html", "raw": ""},
            [],
            _Style(),
            None,
            [],
        )
        assert result is None

    def test_mark_container_applies_underline(self) -> None:
        """The ==mark== syntax (via mark plugin) applies underline."""
        from markdown_to_notion._inline import _apply_container, _Style

        style = _apply_container(_Style(), "mark")
        assert style.underline is True

    def test_unrecognized_html_inside_span(self) -> None:
        """Unrecognized inline HTML inside a span passes through."""
        from markdown_to_notion import convert

        md = '<span color="red"><em>italic</em></span>'
        blocks = convert(md)
        rt = blocks[0]["paragraph"]["rich_text"]
        # Should have items with color annotation
        colored = [it for it in rt if it.get("annotations", {}).get("color") == "red"]
        assert len(colored) >= 1


class TestCalloutColorOnly:
    """Test callout with color but no icon (line 154 in _html.py)."""

    def test_callout_color_no_icon(self) -> None:
        from markdown_to_notion._html import _build_callout

        blocks = _build_callout("Note text", icon="", color="gray_bg")
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["color"] == "gray_bg"
        assert "icon" not in blocks[0]["callout"]


class TestLineBreaks:
    def test_softbreak(self) -> None:
        items = parse_inline(_inline("line1\nline2"))
        newlines = [it for it in items if it["text"]["content"] == "\n"]
        assert len(newlines) >= 1

    def test_linebreak(self) -> None:
        # Two trailing spaces + newline = hard break
        items = parse_inline(_inline("line1  \nline2"))
        newlines = [it for it in items if it["text"]["content"] == "\n"]
        assert len(newlines) >= 1
