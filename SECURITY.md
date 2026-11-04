# Security

ccsearch reads `~/.claude/projects` and writes one cache file,
`~/.cache/claude-session-search/index.json`. The cache holds your session
titles, prompts and project paths, so it's created owner-only. Treat it like
shell history. ccsearch makes no network requests. It starts `claude` with
`exec` and an argument list, without a shell.

Please report vulnerabilities privately via
[GitHub security advisories](https://github.com/alexdoescodes/ccsearch/security/advisories/new).
