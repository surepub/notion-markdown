# AGENTS.md — notion-markdown

## Boundaries

| Always | Ask first | Never |
|--------|-----------|-------|
| Run `pytest --cov --cov-fail-under=100` before opening PRs | Before bumping the version or creating a release | Push directly to `main` — branch protection requires PRs |
| Use `uv` for dependency management | Before adding new dependencies to `pyproject.toml` | Hardcode version strings in tests — they break on every release |
| Keep 100% test coverage | Before changing public API (`convert()`, exported types) | Commit secrets or tokens |

## Release Process

**Releases are tag-driven.** Pushing a `v*` tag triggers `.github/workflows/publish.yml` which builds, publishes to PyPI (trusted publishing), and creates a GitHub Release with auto-generated notes.

Steps to release:
1. Bump `__version__` in `src/notion_markdown/__init__.py` (this is the single source of truth — hatch reads it dynamically)
2. Open a PR for the version bump (can't push to `main` directly)
3. After merge, tag the merge commit: `git tag v<version>` and push the tag: `git push origin v<version>`
4. The publish workflow handles PyPI + GitHub Release automatically

**Never hardcode version assertions in tests** — use `importlib.metadata.version()` if you need to test the version is importable.

## CI

Two workflows in `.github/workflows/`:

- **`ci.yml`** — runs on push to `main` and PRs. Three jobs: `lint` (ruff), `typecheck` (mypy strict), `test` (matrix: Python 3.10–3.13, 100% coverage required)
- **`publish.yml`** — runs on `v*` tag push. Builds with hatchling, publishes to PyPI, creates GitHub Release

CI uses `uv` (via `astral-sh/setup-uv@v4`) for Python and dependency management.

## Architecture

**Functional pipeline:** Markdown string → mistune AST tokens → Notion API block dicts.

- `_html.py` — preprocesses Notion-specific HTML (`<aside>`, `<callout>`, `<details>`, `<span>` with data attributes) before mistune parsing
- `_parser.py` — converts block-level mistune tokens to Notion blocks via `_convert_block()` dispatch
- `_inline.py` — flattens nested inline formatting into flat Notion rich-text with accumulated annotations using `_Style` dataclass
- `_types.py` — all public types are `TypedDict`s for IDE autocomplete and type safety

**Single public entry point:** `convert(markdown: str) -> list[NotionBlock]`

## Conventions

- **Private modules** prefixed with `_` (e.g., `_parser.py`, `_inline.py`)
- **Strict mypy** — `strict = true` in `pyproject.toml`
- **`from __future__ import annotations`** in all source files
- **`Union[X, Y]` not `X | Y`** for runtime type aliases (ruff UP007 is ignored)
- **`typing_extensions.NotRequired`** for optional TypedDict fields
- **Line length:** 100 chars
- **Test files** are exempt from type annotations (`ANN`), unused args (`ARG`), and assert checks (`S101`) via ruff per-file-ignores

## Dependencies

Only two runtime dependencies — keep it minimal:
- `mistune>=3.1,<4` — Markdown parser (AST mode)
- `typing_extensions>=4.0` — backport of `NotRequired`

## Testing

- 100% coverage required (`--cov-fail-under=100`)
- Test structure mirrors source: `test_parser.py`, `test_inline.py`, `test_html.py`, `test_convert.py`
- `test_convert.py` — end-to-end tests through the public `convert()` API
- Other test files test internal modules directly

```bash
# Quick test run
pytest tests/ -v

# Full CI-equivalent run
pytest tests/ --cov=notion_markdown --cov-report=term-missing --cov-fail-under=100 -v
```

<!-- Last audited: 2026-02-12 | Initial creation from session learnings -->
