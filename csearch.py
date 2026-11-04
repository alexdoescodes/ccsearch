#!/usr/bin/env python3
"""csearch - fuzzy search Claude Code sessions and resume one.

Usage:
  csearch <words...>        search, pick with arrow keys, Enter resumes
  csearch                   prompt for the search words
  csearch -p <words...>     print the top matches, no picker
  csearch -n 10 <words...>  show 10 matches instead of 5
  csearch --reindex ...     rebuild the cache from scratch
  csearch --version         print the version

Matches against (strongest first): the session title, the prompts you
typed, and the project directory.

Environment:
  CLAUDE_CONFIG_DIR   Claude Code config dir (default ~/.claude)
  XDG_CACHE_HOME      where the index is cached (default ~/.cache)
"""
import json
import os
import re
import sys
import time
from datetime import datetime

from rapidfuzz import fuzz

__version__ = "0.1.0"

PROJECTS = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "projects")
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "claude-session-search")
CACHE = os.path.join(CACHE_DIR, "index.json")
INDEX_VERSION = 2
# tagged blocks Claude Code injects into user turns that say nothing about the topic
NOISE_RE = re.compile(
    r"<(system-reminder|ide_opened_file|ide_selection|local-command-stdout|local-command-caveat|"
    r"command-message|command-args|bash-stdout|bash-stderr)>.*?</\1>",
    re.S,
)
TAG_RE = re.compile(r"</?[a-zA-Z_-]+(\s[^>]*)?>")
PROMPT_CAP = 600      # chars kept per prompt
PROMPTS_CAP = 12000   # chars kept per session

WEIGHTS = {"title": 1.0, "prompts": 0.85, "project": 0.8}


# ---------------------------------------------------------------- indexing

def encode_path(p):
    """How Claude Code names a project dir: every non-alphanumeric char -> '-'."""
    return re.sub(r"[^a-zA-Z0-9]", "-", p)


def clean_prompt(text):
    text = NOISE_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    return " ".join(text.split())[:PROMPT_CAP]


def user_texts(msg):
    content = msg.get("content")
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return []


def parse_session(path):
    """Pull just the searchable bits out of one transcript."""
    s = {"id": None, "cwds": [], "title": "", "custom_title": "",
         "prompts": [], "first": None, "last": None}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # cheap substring filters before paying for json.loads
            is_user = '"type":"user"' in line
            is_title = '"ai-title"' in line or '"custom-title"' in line or '"type":"summary"' in line
            if not (is_user or is_title):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get("type")
            if t == "ai-title":
                s["title"] = d.get("aiTitle") or s["title"]
            elif t == "custom-title":
                s["custom_title"] = d.get("customTitle") or s["custom_title"]
            elif t == "summary" and not s["title"]:
                s["title"] = d.get("summary") or ""
            elif t == "user":
                if d.get("isSidechain") or d.get("isMeta") or "toolUseResult" in d:
                    continue
                s["id"] = s["id"] or d.get("sessionId")
                cwd = d.get("cwd")
                if cwd and cwd not in s["cwds"]:
                    s["cwds"].append(cwd)
                ts = d.get("timestamp")
                if ts:
                    s["first"] = s["first"] or ts
                    s["last"] = ts
                for txt in user_texts(d.get("message", {})):
                    c = clean_prompt(txt)
                    if c:
                        s["prompts"].append(c)
    if not s["prompts"]:
        return None
    s["id"] = s["id"] or os.path.basename(path)[:-6]
    # resume must run from the dir the session was filed under
    proj = os.path.basename(os.path.dirname(path))
    s["cwd"] = next((c for c in s["cwds"] if encode_path(c) == proj), s["cwds"][0] if s["cwds"] else "")
    s["proj_dir"] = proj
    joined, total = [], 0
    for p in s["prompts"]:
        if total + len(p) > PROMPTS_CAP:
            break
        joined.append(p)
        total += len(p)
    s["prompts"] = joined
    del s["cwds"]
    return s


def session_files():
    try:
        dirs = os.listdir(PROJECTS)
    except FileNotFoundError:
        return
    for d in dirs:
        full = os.path.join(PROJECTS, d)
        if not os.path.isdir(full):
            continue
        for f in os.listdir(full):  # top level only: subagent transcripts live deeper
            if f.endswith(".jsonl"):
                yield os.path.join(full, f)


def load_index(rebuild=False):
    cache = {}
    if not rebuild:
        try:
            with open(CACHE) as fh:
                data = json.load(fh)
            if data.get("version") == INDEX_VERSION:
                cache = data["files"]
        except (OSError, ValueError, KeyError):
            pass
    files, changed = {}, False
    for path in session_files():
        try:
            st = os.stat(path)
        except OSError:
            continue
        key = [st.st_mtime_ns, st.st_size]
        hit = cache.get(path)
        if hit and hit["key"] == key:
            files[path] = hit
            continue
        try:
            files[path] = {"key": key, "s": parse_session(path)}
        except OSError:
            continue
        changed = True
    if changed or len(files) != len(cache):
        # the index holds your prompts: keep it private like shell history
        os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)
        tmp = CACHE + ".tmp"
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as fh:
            json.dump({"version": INDEX_VERSION, "files": files}, fh)
        os.replace(tmp, CACHE)
    return [v["s"] for v in files.values() if v["s"]]


# ---------------------------------------------------------------- scoring

def display_title(s):
    return s["custom_title"] or s["title"] or s["prompts"][0]


def score(s, query, tokens):
    fields = {
        "title": (s["custom_title"] + " " + s["title"]).strip().lower(),
        "prompts": " \n ".join(s["prompts"]).lower(),
        "project": s["cwd"].replace(os.path.expanduser("~"), "~").lower(),
    }
    fields = {k: v for k, v in fields.items() if v}

    # every word should show up somewhere (typos allowed)
    per_token = []
    for tok in tokens:
        best = 0.0
        for k, text in fields.items():
            best = max(best, WEIGHTS[k] * fuzz.partial_ratio(tok, text))
            if best >= 100 * WEIGHTS["title"]:
                break
        per_token.append(best)
    token_score = sum(per_token) / len(per_token)

    # bonus for the whole phrase landing in one place
    phrase = 0.0
    if len(tokens) > 1:
        phrase = max(WEIGHTS[k] * fuzz.partial_ratio(query, text) for k, text in fields.items())

    # small nudge toward recent sessions
    recency = 0.0
    if s["last"]:
        try:
            age = time.time() - datetime.fromisoformat(s["last"].replace("Z", "+00:00")).timestamp()
            recency = max(0.0, 3.0 * (1 - age / (90 * 86400)))
        except ValueError:
            pass
    return 0.7 * token_score + 0.3 * (phrase or token_score) + recency


def best_line(s, tokens):
    """The prompt that matches best, for showing under the title."""
    best, best_sc = "", -1
    for p in s["prompts"]:
        sc = sum(fuzz.partial_ratio(t, p.lower()) for t in tokens)
        if sc > best_sc:
            best, best_sc = p, sc
    return best


def search(sessions, query, n):
    query = " ".join(query.lower().split())
    tokens = query.split()
    ranked = sorted(((score(s, query, tokens), s) for s in sessions), key=lambda x: -x[0])
    return ranked[:n]


# ---------------------------------------------------------------- display

def short(text, width):
    text = " ".join(text.split())
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def fmt_when(ts):
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts[:16]


def rows_for(results, tokens, width):
    out = []
    for sc, s in results:
        home = os.path.expanduser("~")
        d = resume_dir(s)
        proj = d.replace(home, "~", 1) if d else "?"
        out.append((
            short(display_title(s), width - 4),
            short(f"{proj}  ·  {fmt_when(s['last'])}  ·  score {sc:.0f}", width - 4),
            short("› " + best_line(s, tokens), width - 4),
        ))
    return out


def print_results(results, tokens):
    width = os.get_terminal_size().columns if sys.stdout.isatty() else 120
    for i, (r, (_, s)) in enumerate(zip(rows_for(results, tokens, width), results, strict=True), 1):
        print(f"{i}. {r[0]}\n   {r[1]}\n   {r[2]}\n   id {s['id']}\n")


def pick(results, tokens):
    """Arrow-key picker on /dev/tty. Returns the chosen session or None."""
    import termios
    import tty

    tty_fd = os.open("/dev/tty", os.O_RDWR)
    out = os.fdopen(tty_fd, "w", buffering=1)
    width = os.get_terminal_size(tty_fd).columns or 100
    rows = rows_for(results, tokens, width)
    sel = 0
    height = len(rows) * 4 + 1

    def draw(first):
        if not first:
            out.write(f"\x1b[{height}A")
        for i, r in enumerate(rows):
            on = i == sel
            mark = "\x1b[1;36m❯\x1b[0m" if on else " "
            title = f"\x1b[1;7m {r[0]} \x1b[0m" if on else f"\x1b[1m {r[0]} \x1b[0m"
            out.write(f"\x1b[2K{mark} {title}\r\n\x1b[2K   \x1b[2m{r[1]}\x1b[0m\r\n"
                      f"\x1b[2K   \x1b[3m{r[2]}\x1b[0m\r\n\x1b[2K\r\n")
        out.write("\x1b[2K\x1b[2m↑/↓ move · Enter resume · 1-9 jump · Esc quit\x1b[0m\r\n")
        out.flush()

    old = termios.tcgetattr(tty_fd)
    try:
        tty.setraw(tty_fd)
        out.write("\x1b[?25l")
        draw(True)
        while True:
            ch = os.read(tty_fd, 3)
            if ch in (b"\x1b[A", b"k") and sel > 0:
                sel -= 1
            elif ch in (b"\x1b[B", b"j") and sel < len(rows) - 1:
                sel += 1
            elif ch in (b"\r", b"\n"):
                return results[sel][1]
            elif ch in (b"\x1b", b"q", b"\x03", b"\x04"):
                return None
            elif ch.isdigit() and 1 <= int(ch) <= len(rows):
                return results[int(ch) - 1][1]
            draw(False)
    finally:
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old)
        out.write("\x1b[?25h")
        out.flush()


def decode_proj_dir(enc, base="/"):
    """Find an existing dir whose encoded path equals `enc` (the encoding is lossy,
    so walk the filesystem and match segment by segment)."""
    if not enc:
        return base
    try:
        children = os.listdir(base)
    except OSError:
        return None
    for c in children:
        full = os.path.join(base, c)
        e = encode_path("/" + c)
        if (enc == e or enc.startswith(e + "-")) and os.path.isdir(full):
            hit = decode_proj_dir(enc[len(e):], full)
            if hit:
                return hit
    return None


def resume_dir(s):
    """Claude finds a session by the project dir it is filed under, so resume from
    the directory that maps to it; projects that moved need the filesystem walk."""
    if s["cwd"] and encode_path(s["cwd"]) == s["proj_dir"] and os.path.isdir(s["cwd"]):
        return s["cwd"]
    return decode_proj_dir(s["proj_dir"]) or s["cwd"]


def resume(s):
    cwd = resume_dir(s)
    if not cwd or not os.path.isdir(cwd):
        sys.exit(f"csearch: the session's directory no longer exists: {cwd or '?'}\n"
                 f"    session id: {s['id']}")
    os.chdir(cwd)
    print(f"→ {cwd}\n→ claude --resume {s['id']}", file=sys.stderr)
    os.execvp("claude", ["claude", "--resume", s["id"]])


# ---------------------------------------------------------------- main

def main(argv):
    n, printing, rebuild, words = 5, False, False, []
    it = iter(argv)
    for a in it:
        if a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        elif a in ("-p", "--print"):
            printing = True
        elif a == "--reindex":
            rebuild = True
        elif a in ("-V", "--version"):
            print(f"csearch {__version__}")
            return 0
        elif a == "-n":
            val = next(it, "")
            if not val.isdigit() or int(val) < 1:
                print("csearch: -n needs a positive number", file=sys.stderr)
                return 2
            n = int(val)
        else:
            words.append(a)
    query = " ".join(words).strip()
    if not query:
        if not sys.stdin.isatty():
            print(__doc__.strip(), file=sys.stderr)
            return 2
        query = input("search sessions: ").strip()
        if not query:
            return 0

    sessions = load_index(rebuild)
    if not sessions:
        sys.exit("csearch: no sessions found under " + PROJECTS)
    results = search(sessions, query, n)
    tokens = " ".join(query.lower().split()).split()
    if printing or not sys.stdout.isatty():
        print_results(results, tokens)
        return 0
    chosen = pick(results, tokens)
    if chosen:
        resume(chosen)
    return 0


def cli():
    """Console-script entry point."""
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    cli()
