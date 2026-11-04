import json
import os

import pytest

import csearch as cs


def line(d):
    return json.dumps(d, separators=(",", ":"))


def user(text, cwd, sid="sess-1", ts="2026-11-01T10:00:00Z", **extra):
    return line({"type": "user", "sessionId": sid, "cwd": cwd, "timestamp": ts,
                 "message": {"content": text}, **extra})


def write_session(projects, cwd, sid, lines):
    d = projects / cs.encode_path(str(cwd))
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.jsonl").write_text("\n".join(lines) + "\n")
    return d / f"{sid}.jsonl"


@pytest.fixture
def env(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    cache = tmp_path / "cache"
    projects.mkdir()
    monkeypatch.setattr(cs, "PROJECTS", str(projects))
    monkeypatch.setattr(cs, "CACHE_DIR", str(cache))
    monkeypatch.setattr(cs, "CACHE", str(cache / "index.json"))
    return tmp_path, projects


def test_encode_path_matches_claude_code():
    assert cs.encode_path("/home/a/Dev/my.app_x") == "-home-a-Dev-my-app-x"


def test_parse_keeps_typed_prompts_and_drops_noise(env):
    tmp, projects = env
    cwd = tmp / "proj"
    p = write_session(projects, cwd, "s1", [
        user("<system-reminder>ignore me</system-reminder>fix the backup job", str(cwd), sid="s1"),
        user("tool output", str(cwd), sid="s1", toolUseResult={}),
        user("meta", str(cwd), sid="s1", isMeta=True),
        line({"type": "ai-title", "aiTitle": "Backup job fix", "sessionId": "s1"}),
        line({"type": "assistant", "message": {"content": [{"type": "text", "text": "replies are not indexed"}]}}),
    ])
    s = cs.parse_session(str(p))
    assert s["id"] == "s1"
    assert s["prompts"] == ["fix the backup job"]
    assert s["title"] == "Backup job fix"
    assert s["cwd"] == str(cwd)


def test_custom_title_wins_for_display(env):
    tmp, projects = env
    p = write_session(projects, tmp, "s2", [
        user("hello", str(tmp), sid="s2"),
        line({"type": "ai-title", "aiTitle": "Auto"}),
        line({"type": "custom-title", "customTitle": "Mine"}),
    ])
    assert cs.display_title(cs.parse_session(str(p))) == "Mine"


def test_session_without_prompts_is_skipped(env):
    tmp, projects = env
    p = write_session(projects, tmp, "s3", [line({"type": "ai-title", "aiTitle": "x"})])
    assert cs.parse_session(str(p)) is None


def test_subagent_transcripts_are_not_indexed(env):
    tmp, projects = env
    write_session(projects, tmp, "top", [user("top level", str(tmp), sid="top")])
    sub = projects / cs.encode_path(str(tmp)) / "top" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent.jsonl").write_text(user("subagent", str(tmp), sid="agent") + "\n")
    assert [s["id"] for s in cs.load_index()] == ["top"]


def test_search_ranks_topic_match_first_and_tolerates_typos(env):
    tmp, projects = env
    write_session(projects, tmp / "a", "docker", [user("my docker volume backups keep failing", str(tmp / "a"),
                                                       sid="docker")])
    write_session(projects, tmp / "b", "css", [user("make the navbar sticky in css", str(tmp / "b"), sid="css")])
    sessions = cs.load_index()
    top = cs.search(sessions, "dokcer volume", 2)
    assert top[0][1]["id"] == "docker"


def test_project_path_counts(env):
    tmp, projects = env
    write_session(projects, tmp / "harbor", "h", [user("add login", str(tmp / "harbor"), sid="h")])
    write_session(projects, tmp / "other", "o", [user("add login", str(tmp / "other"), sid="o")])
    top = cs.search(cs.load_index(), "harbor login", 2)
    assert top[0][1]["id"] == "h"


def test_index_cache_is_reused_until_file_changes(env, monkeypatch):
    tmp, projects = env
    p = write_session(projects, tmp, "c", [user("first", str(tmp), sid="c")])
    cs.load_index()
    calls = []
    real = cs.parse_session
    monkeypatch.setattr(cs, "parse_session", lambda path: calls.append(path) or real(path))
    cs.load_index()
    assert calls == []
    p.write_text(p.read_text() + user("second prompt", str(tmp), sid="c") + "\n")
    os.utime(p, ns=(1, 1))
    assert cs.load_index()[0]["prompts"] == ["first", "second prompt"]
    assert calls == [str(p)]


def test_resume_dir_follows_moved_projects(env):
    tmp, projects = env
    new = tmp / "new" / "proj"
    new.mkdir(parents=True)
    # filed under the new location, but recorded with the old cwd
    p = write_session(projects, new, "m", [user("hi", str(tmp / "old" / "proj"), sid="m")])
    s = cs.parse_session(str(p))
    assert cs.resume_dir(s) == str(new)


def test_cli_print_mode(env, capsys):
    tmp, projects = env
    write_session(projects, tmp, "p", [user("render the invoice pdf", str(tmp), sid="p")])
    assert cs.main(["-p", "invoice"]) == 0
    out = capsys.readouterr().out
    assert "render the invoice pdf" in out and "id p" in out


def test_cli_rejects_bad_count(capsys):
    assert cs.main(["-n", "zero", "x"]) == 2
