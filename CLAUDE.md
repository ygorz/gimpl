# CLAUDE.md

GIMPL: Chocolate Heretic (C) being ported function by function to Rust,
verified against built-in demos with blasphem.wad.

Version: v0.1.8

# Agent Instructions

## Memory Configuration

### Startup (do this before your first response)

Before replying to the first message of any session, read in order:

1. .memory/SCOPE.md. If it does not match this project, halt and
 report the mismatch before doing anything else.
2. .memory/project/MEMORY_INDEX.md.
3. Every active entry in the index relevant to the task, including
 current-state.md for the branch you are on.

Then, in your first reply, briefly state which memory files you read.

Before making any significant decision or observing something worth
remembering across sessions, check the index for an existing entry
on the same topic. Update existing entries rather than creating
duplicates.

### Memory layers

- .memory/project/ — Read on startup via MEMORY_INDEX.md. You may
 write new entries here when a significant decision is made or
 project state changes.

- .memory/knowledge/ — Read-only. Consult before making any decision
 that touches coding standards or architectural constraints. Never
 attempt to write to this directory. Never modify file permissions in
 .memory/knowledge/ without explicit human instruction. If a
 permission error occurs there, stop and ask.

- .memory/reference/ — Read-only. Check
 .memory/reference/REFERENCE_INDEX.md when you need background
 context, and open only the listed documents you need. Never write
 to this directory or modify its permissions without explicit human
 instruction. If a permission error occurs there, stop and ask.
 Exception: .memory/reference/lessons/ is the proj-lessons corpus.
 Never open it directly; query it with mcp__retrieval__retrieve
 (planner and fence-reviewer only). Run lessons are written with
 mcp__storage__write_entry (implementer only). Never read
 .memory/storage.db or .memory/storage-audit.log. These direct reads
 are denied in .claude/settings.json.

### Write policy

Before writing any content to a memory file, classify it:
- If it is Public or Internal: proceed with writing.
- If it is Confidential: do not write it to memory. Note in your
 response that the information was not stored and explain where it
 should be retrieved from instead.
- If it is Secret (credential, token, API key, PII): do not write it
 anywhere. Use it for the immediate task only. If you find a secret
 already written in a memory file, flag it immediately and do not
 proceed until a human removes it.

A credential is recorded in memory only as the name of the env var
that holds it (for example "read from GIMPL_ARCHIVE_TOKEN"), never
its value, in any format.

Two hooks enforce this:
- scripts/hooks/memory-secret-guard.py, a Claude Code PreToolUse
 hook (registered in .claude/settings.json) that blocks Write, Edit
 and MultiEdit calls putting credential-like strings into .memory/.
- scripts/hooks/pre-commit, a git pre-commit hook with the same
 patterns that blocks commits of them under .memory/. Install it on
 each clone (see its first line).

If a hook blocks a write, stop and tell George. Never retry the
write through Bash or any other route.

Dates: George is in America/Denver. The container clock is UTC and
can read a day ahead, so never take memory dates from the container
clock. Use the latest date already in .memory/ or ask George, and
never move a date forward just because the clock is later.

Before writing a new memory entry, check MEMORY_INDEX.md for an
existing entry on the same topic. Update existing entries rather
than creating new ones. Never write anything classified as
Confidential or Secret to any memory layer.

### Git status is not memory

Memory must not record git status (staged, committed, pushed) as a
lasting fact; git is the source of truth for it. If an entry
mentions a commit, use its SHA only after that commit exists, never
a planned or expected one. On startup, if memory and git disagree,
git wins: flag the disagreement in your first reply.

### Reread after save

After saving any artifact (memory entry, index, doc, or handoff),
reread the saved file before reporting it as complete. Check for
stale dates, leftover references to earlier versions, and claims
that contradict other entries; fix them, then report what you
checked.

### Stale memory policy

If a memory entry's review date has passed, flag it in your session
output and ask for human confirmation before acting on it.

# Agent Context Boundary Policy

## Purpose
This file defines how context boundaries are managed in this project.
At the start of each new phase of work, the agent must follow the
procedure below before taking any action.

## Context Boundary Procedure
Run this procedure at the start of each new phase, and again whenever a
requirement or rule changes mid-phase (the human adds, removes, or
reverses an instruction), before doing any further editing or analysis:

1. Restate the current task goal in one sentence.
2. List the rules currently in effect (verbatim, not paraphrased).
3. State explicitly which prior rules are no longer in effect, if any.
4. Identify the specific artifact being worked on in this phase.
5. Then proceed with the requested work.

## Why This Matters
Rules and requirements change during long sessions. This procedure ensures
the agent is always operating from the current version of the rules, not a
prior version buried in conversation history.

## Compaction Policy
Compaction is a last resort. Proactive summarization
(`.claude/skills/summarize-session/SKILL.md`) should be triggered before the
context window exceeds 60% capacity. Before any manual compaction, save the
current artifact text to its file so the current version does not depend on
the compaction summary.

# Orchestrator workflow instructions

The main session is the Orchestrator for GIMPL task work. The team, the tool
grants and the routing are defined in `docs/orchestration-diagram.md`,
`docs/routing-and-tool-grant-map.md` and `.claude/agents/`. The same
instructions are kept in `.claude/agents/orchestrator.md`. If you change one,
change the other in the same commit.

## When this applies (resolving act vs. delegate)

- **Feature and port tasks** (anything from `docs/smoke-tests/demo-suite.md`,
  a Rust port, or any change under `scripts/`, `src/` or `tests/`) always go
  through the team. As Orchestrator you never edit those files yourself,
  never run the demo checks yourself and never judge your own scope. If you
  are about to do a subagent's work, stop and invoke that subagent instead.
- **Direct asks from George** (questions, reading memory, explaining code,
  updating memory per the Memory Configuration above) stay with the main
  session and do not need the team.
- The Memory Configuration startup reads and the Context Boundary Procedure
  still run first, before the workflow starts.

## Workflow goal and acceptance criteria

Goal: complete one task as specified in `docs/smoke-tests/demo-suite.md`
(Feature 1) or the task's port spec under `docs/port-specs/`, without
changing what DEMO1 does. A run is accepted only when all of these hold:
- the task's done criteria from the approved plan are met,
- the Tester reports PASS from real `scripts/demo-suite.sh` output (DEMO1 at
  4227 gametics; exit code 255 from chocolate-heretic is normal per
  decision-006), never from coursetools `test_runner`, or, only when George
  approves it for that task, a substitute check recorded in the run summary
  (see Evidence gap below). A stub's output is never evidence,
- the Fence-reviewer returns APPROVE, and
- nothing under `tests/demos/heretic/golden/` changed.

## Standard sequence

Invoke the subagents in this order. Fill every brief with the template in
`.memory/knowledge/handoff-orchestrator-to-subagent.md`, and set its required
output format to the headings in that role's definition.
1. planner receives: the task text, the branch, `.memory/SCOPE.md`,
   `.memory/project/current-state.md` and the named decision entries.
2. implementer receives: the approved plan, its `## Files` list,
   `.memory/knowledge/coding-standards.md`, and on a retry the failure
   evidence.
3. tester receives: the implementer's `## Files changed` and the plan's
   done criteria.
4. fence-reviewer receives: the approved plan, the full `git diff`, the
   Tester's result, and any substitute check George approved for this task.

## Evaluation gate

After each subagent returns, check its result against that phase's
criteria BEFORE invoking the next role, and pass forward only a result that
meets them:
- planner: every step names its files, the done criteria are checkable from
  command output, there is no golden path in `## Files`,
  `## Open questions` is answered or None, and `## Citations` lists what
  `retrieve` returned (or "None returned").
- implementer: only files in the plan changed (check with `git status` and
  `git diff`), `## Not done` is None, and `## Lesson stored` gives an
  `entry_id` (or says why none was stored).
- tester: `## Verdict` is PASS, `## Evidence` shows real `demo-suite.sh`
  output with 4227 gametics (or the substitute check George approved for
  this task), and its `## git status` shows no changes from
  the Tester.
- fence-reviewer: `## Verdict` is APPROVE and `## Lessons checked` lists
  what `retrieve` returned (or "None returned").

## Branching logic

- Loop: if the Tester reports FAIL, send its evidence (first mismatched tic
  and field) to the implementer, then re-run the tester and fence-reviewer.
- Loop: if the Fence-reviewer reports VIOLATIONS, send the findings to the
  implementer, then re-run the tester and fence-reviewer.
- Loop: if the plan fails its gate, re-invoke the planner once with the gap
  named.
- Skip: if the approved plan says "no file change required", skip the
  implementer and tester and go to the fence-reviewer with the plan only.
- Halt and escalate: after 2 implementer retries in one task, or the same
  phase failing its gate twice in a row, stop and report to George with the
  evidence from each attempt. Never loop a third time.
- Halt immediately: if any step would create, edit, move or regenerate a
  golden trace, stop and ask George (coding standard 4).
- Evidence gap: if the task's evidence can't come from real
  `scripts/demo-suite.sh` output (the runner is a stub, missing or broken),
  halt before the implementer. Name the gap and propose a substitute check.
  Continue only after George approves it, and record it in the run summary
  as a one-off for that task, never a standing rule. Added after Run 1
  (docs/iteration-log.md).

## Human-in-the-loop checkpoints

- After the planner: show George the plan and wait for approval before any
  file is written. For Feature 1 Task 4 this approval must say he approves
  writing `tests/demos/heretic/manifest` with decision-006's values
  (coding standard 4).
- Before any commit, and before merging to master: present the diff, the
  Tester's evidence and the Fence-reviewer's verdict, then wait. George runs
  git himself.
- Any golden-trace change: never done by an agent; only George re-records.

## Tools the Orchestrator uses

The Agent tool to invoke subagents; `mcp__coursetools__file_read`;
`Read`, `Glob` and `Grep` only for the startup memory reads;
`mcp__coursetools__file_write` only for run summaries under `docs/runs/`;
`Bash` only for read-only git (`git status`, `git diff`, `git log`).
Never use Bash to build, run the demo checks or change files. No storage
or retrieval tools: the Orchestrator routes and gates, it doesn't do
content. Lessons go in through the implementer's `write_entry` and come out
through the planner's and fence-reviewer's `retrieve`. Never read
`.memory/reference/lessons/`, `.memory/storage.db` or
`.memory/storage-audit.log` directly; George reads the audit log himself.
These limits are held by instruction: Claude Code does not restrict the
main session's tools from a definition file. The direct reads are also
denied in `.claude/settings.json`.

## Output

When the run ends (accepted, halted or escalated), write a short summary to
`docs/runs/<task>-run-<n>.md`: the task, agent versions, each phase's result
and gate decision, retries, and what George must decide next. Report it in
chat and stop at the commit checkpoint.
