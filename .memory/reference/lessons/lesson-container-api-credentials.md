---
classification: confidential
project: proj-lessons
doc_type: lesson
---

## Lesson: How the container gets API access, and how credentials are handled

**What happened.** Claude Code inside the GIMPL container needs its API login, and nothing else in the project needs a credential. The login is kept in the `claude-auth` named volume mounted at `/claude-auth`, which persists only the Claude Code credential file between sessions. The host `~/.claude` folder is never mounted, the container has no `/root/.ssh`, and the repo references no credential environment variables. Since Module 3 the course's OpenRouter key also reaches the container, but only as the `OPENROUTER_API_KEY` env var passed with `-e` at `docker run`; it is never written to the repo or `.memory/`. In Run 003 the saved login had expired, so the session had to sign in again before the timed run.

**What we learned.** A credential is recorded in memory only as the name of the env var that holds it, such as `ANTHROPIC_API_KEY` or `GIMPL_ARCHIVE_TOKEN`, never its value in any format. Two hooks enforce this with the same patterns: `scripts/hooks/memory-secret-guard.py`, a PreToolUse hook that blocks Write, Edit and MultiEdit calls putting credential-like strings into `.memory/`, and `scripts/hooks/pre-commit`, which blocks commits of them. Known gaps: the commit hook covers only `.memory/`, it must be installed on each clone, and an earlier lesson's fake key is still in git history at 5bffcbdb.

**How to apply it.** Re-sign in to the `claude-auth` volume before a long session rather than mid-run, and never mount a host credential folder instead. If a hook blocks a write, stop and tell George; never retry the write through Bash or any other route. Never paste a credential value into memory, docs, run summaries or retrieval results. A real leaked key would be revoked, with history and clones treated as exposed.
