# Contributing

Thanks for wanting to help. csearch is deliberately small: one module, one
dependency, no config file. Changes that keep it that way are the easiest to
merge.

## Setup

```sh
git clone https://github.com/alexdoescodes/csearch
cd csearch
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

```sh
ruff check .
pytest -q
```

- Add a test for anything that changes how sessions are parsed or ranked.
  Tests build tiny fake transcripts in a temp dir. **Never commit real
  session data**, not even redacted.
- Add a line under **Unreleased** in `CHANGELOG.md`.
- Keep the picker dependency-free (plain `termios`, no curses/TUI libraries).

## When Claude Code changes its transcript format

csearch reads Claude Code's internal `~/.claude/projects/**/*.jsonl` files,
which are not a public API. If a Claude Code update breaks parsing, an issue
with your `claude --version` and the *shape* of the new lines (keys and types,
no content) is the most useful thing you can send. Bump `INDEX_VERSION` in
`csearch.py` whenever the parsed fields change so existing caches rebuild.

## Releasing (maintainers)

1. Move **Unreleased** in `CHANGELOG.md` to a new version heading.
2. Bump `__version__` in `csearch.py`.
3. Commit, then `git tag vX.Y.Z && git push --tags`. The release workflow
   builds the wheel and publishes the GitHub release.
