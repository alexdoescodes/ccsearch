# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Renamed from `csearch` to `ccsearch` (command, package and repository) to
  avoid sounding like a C tool. The old GitHub URL redirects. The cache
  location is unchanged.

## [0.1.0] - 2026-11-04

Released as `csearch`.

### Added

- Fuzzy search across every Claude Code session by title, typed prompts and
  project path, typo-tolerant via rapidfuzz.
- Top-N results (default 5) in an arrow-key picker; Enter resumes, `1`–`9`
  jump, `j`/`k` move, Esc quits.
- Resume from any directory: csearch switches to the session's project dir
  and runs `claude --resume <id>`, following projects that have moved.
- Incremental index cache in `$XDG_CACHE_HOME/claude-session-search`.
- `-p` print mode, `-n` result count, `--reindex`, `--version`.
- `CLAUDE_CONFIG_DIR` support.

[Unreleased]: https://github.com/alexdoescodes/ccsearch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alexdoescodes/ccsearch/releases/tag/v0.1.0
