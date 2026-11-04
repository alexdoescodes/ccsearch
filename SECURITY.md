# Security

## What csearch touches

- **Reads** Claude Code transcripts under `~/.claude/projects` (or
  `$CLAUDE_CONFIG_DIR/projects`).
- **Writes** one cache file, `~/.cache/claude-session-search/index.json`,
  holding session titles, the prompts you typed, and project paths. New
  caches are created owner-only (`0700` dir, `0600` file); treat it like
  your shell history.
- **Runs** `claude --resume <id>` in the session's project directory, via
  `exec` with an argument list — no shell is involved.
- **Never** makes network requests or sends data anywhere.

To wipe the cache: `rm -rf ~/.cache/claude-session-search`.

## Reporting a vulnerability

Please report privately through
[GitHub security advisories](https://github.com/alexdoescodes/csearch/security/advisories/new)
rather than a public issue. You'll get a reply within a week.
