"""Tests for the CLI."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from notion_markdown._cli import main


class TestToNotionStdout:
    def test_file_to_stdout(self, tmp_path, capsys):
        md = tmp_path / "input.md"
        md.write_text("# Hello\n\nWorld\n")
        main(["to-notion", str(md)])
        out = capsys.readouterr().out
        blocks = json.loads(out)
        assert blocks[0]["type"] == "heading_1"

    def test_stdin_to_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", open(tmp_path / "in.md", "w+"))  # noqa: SIM115, PTH123
        (tmp_path / "in.md").write_text("**bold**\n")
        monkeypatch.setattr("sys.stdin", open(tmp_path / "in.md"))  # noqa: SIM115, PTH123
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        main(["to-notion"])
        out = capsys.readouterr().out
        blocks = json.loads(out)
        assert blocks[0]["type"] == "paragraph"
        assert any(
            rt.get("annotations", {}).get("bold") for rt in blocks[0]["paragraph"]["rich_text"]
        )


class TestToNotionOutputFile:
    def test_file_to_output_file(self, tmp_path):
        md = tmp_path / "input.md"
        md.write_text("- item 1\n- item 2\n")
        out = tmp_path / "output.json"
        main(["to-notion", str(md), "-o", str(out)])
        blocks = json.loads(out.read_text())
        assert len(blocks) == 2
        assert all(b["type"] == "bulleted_list_item" for b in blocks)

    def test_compact_json(self, tmp_path):
        md = tmp_path / "input.md"
        md.write_text("Hello\n")
        out = tmp_path / "output.json"
        main(["to-notion", str(md), "-o", str(out), "--indent", "0"])
        text = out.read_text().strip()
        assert "\n" not in text


class TestToNotionEdgeCases:
    def test_no_input_exits(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        with pytest.raises(SystemExit, match="2"):
            main(["to-notion"])

    def test_empty_file(self, tmp_path, capsys):
        md = tmp_path / "empty.md"
        md.write_text("")
        main(["to-notion", str(md)])
        out = capsys.readouterr().out
        assert json.loads(out) == []


class TestToMarkdownStdout:
    def test_file_to_stdout(self, tmp_path, capsys):
        rt = [{"type": "text", "text": {"content": "Hello"}}]
        blocks = [{"type": "heading_1", "heading_1": {"rich_text": rt, "is_toggleable": False}}]
        jf = tmp_path / "input.json"
        jf.write_text(json.dumps(blocks))
        main(["to-markdown", str(jf)])
        out = capsys.readouterr().out
        assert "# Hello" in out

    def test_stdin_to_stdout(self, tmp_path, monkeypatch, capsys):
        rt = [{"type": "text", "text": {"content": "hi"}}]
        blocks = [{"type": "paragraph", "paragraph": {"rich_text": rt}}]
        jf = tmp_path / "in.json"
        jf.write_text(json.dumps(blocks))
        monkeypatch.setattr("sys.stdin", open(jf))  # noqa: SIM115, PTH123
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        main(["to-markdown"])
        out = capsys.readouterr().out
        assert "hi" in out

    def test_output_file(self, tmp_path):
        blocks = [{"type": "divider", "divider": {}}]
        jf = tmp_path / "input.json"
        jf.write_text(json.dumps(blocks))
        out = tmp_path / "output.md"
        main(["to-markdown", str(jf), "-o", str(out)])
        assert "---" in out.read_text()

    def test_invalid_json_not_list(self, tmp_path):
        jf = tmp_path / "bad.json"
        jf.write_text('{"type": "paragraph"}')
        with pytest.raises(SystemExit, match="2"):
            main(["to-markdown", str(jf)])

    def test_no_input_exits(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        with pytest.raises(SystemExit, match="2"):
            main(["to-markdown"])


class TestNoCommand:
    def test_no_args_exits(self):
        with pytest.raises(SystemExit, match="2"):
            main([])


class TestVersion:
    def test_version_flag(self):
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "notion_markdown._cli", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "notion-markdown" in result.stdout
