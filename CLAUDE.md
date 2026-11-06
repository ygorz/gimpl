# CLAUDE.md

GIMPL: Chocolate Heretic (C) being ported function by function to Rust,
verified against built-in demos with blasphem.wad.

Version: v0.1.1

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

### Write policy

Before writing a new memory entry, check MEMORY_INDEX.md for an
existing entry on the same topic. Update existing entries rather
than creating new ones. Never write anything classified as
Confidential or Secret to any memory layer.

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
