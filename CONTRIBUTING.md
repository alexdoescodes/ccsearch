# Contributing

Issues and PRs are welcome. ccsearch is meant to stay one file with one
dependency.

```sh
pip install -e ".[dev]"
ruff check . && pytest -q
```

Tests build small fake transcripts in a temp dir. Please don't commit real
session data. If a Claude Code update breaks parsing, an issue with your
`claude --version` and the shape of the new JSONL lines (keys only, no
content) is the most useful thing you can send.
