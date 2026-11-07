# Memory Architecture

## What this workflow needs to remember
This agent helps develop GIMPL by porting Chocolate Heretic from C to Rust and checking that game behavior stays consistent with the original. Across sessions, it needs to remember agreed decisions and their reasons, unresolved questions, constraints, deferred alternatives, the current phase, and the next action. It should reference code, tests, and documentation rather than duplicate information already preserved there. It must not store credentials, unrelated personal data, or expired task details, and permissions granted for one session must not automatically carry into another.

## Layer 1: Project memory directory

### Belongs here
- Why Feature 1 uses committed reference traces and a bash runner.
- Why the pinned C reference-build alternative is deferred.
- Current Feature 1 status and next action, tied to its branch and commit.
- Unresolved decisions, such as the exact trace format.

### Does not belong here
- Full traces or source code: those already belong in project artifacts.
- Credentials: memory must not contain secrets.
- Old session permissions: they must not become ongoing authorization.

### Scope
GIMPL only. Feature-specific entries identify their branch so unfinished work is not mistaken for project-wide state.

### Write permissions
The agent may update status and record agreed decisions within the authorized task. It may not invent decisions or override human-controlled rules. Changes receive human review before commit.

### Pruning policy
Check status against the repo when resuming and update it when stopping. At feature completion, remove obsolete next actions and archive the handoff. Retain decision rationale while it remains relevant; mark superseded decisions explicitly.


## Layer 2: Knowledge files

### Belongs here
- Preserve original C behavior when porting to Rust.
- Do not regenerate or change approved reference traces without human approval.
- Follow the Context Boundary Procedure at phase boundaries and when requirements change mid-phase.
- Reread saved artifacts for stale claims before treating them as complete.

### Does not belong here
- Current branch status or next actions: these change frequently and belong in project memory.
- Large transcripts or trace output: these are evidence, not standing rules.

### Scope
Project-wide rules for GIMPL. Any narrower exception must be explicit and limited to its authorized task.

### Write permissions
Human-controlled and read-only for the agent by default. The agent may propose changes, but edits require explicit human approval.

### Pruning policy
Review when project policy changes or a conflict is found. Humans approve replacements and remove obsolete rules; preserve the reason for significant changes in version history.

## Layer 3: Indexed reference documents

### Current state
Intentionally empty. `.memory/reference/REFERENCE_INDEX.md` exists and lists no documents. GIMPL's port specs, demo-check docs, handoffs, and the iteration log already live in `docs/` and are found by searching the repo, so copying or indexing them here would only duplicate them.

### Belongs here (when added)
- Large, rarely needed documents that should be looked up on demand rather than loaded at startup, such as a DOOM/Heretic data-format spec or a long C-to-Rust mapping table.
- Each entry in the index: file name, one-line summary, when to consult it, and date added.

### Does not belong here
- Copies of documents already in `docs/`: link to the authoritative file instead.
- Unlabeled old handoffs presented as current instructions: historical material must not override current rules.

### Trigger to add the first entry
A fresh session repeatedly needs the same large outside document, or a document is too big to read on every startup.

### Scope
GIMPL reference material only.

### Write permissions
Human-controlled. The directory is read-only (555) like the knowledge directory; the agent may propose index entries but a human adds them.

### Pruning policy
Check entries when documents move or features finish. Remove broken entries and label superseded documents as historical.

## Why the write boundaries are drawn here
- Knowledge files are human-only because they hold the rules that keep the port honest. If the agent could edit them, it could quietly loosen a rule like "reference traces need human approval" to make a failing demo pass, and nothing would flag it.
- Project memory is agent-writable because status and next actions change every session; requiring a human for each update would make memory go stale. Human review before commit is the check.
- Permissions are enforced by the filesystem (555 directories, 444 files), not only by instructions, and were verified inside the container: even as root, `touch` and `chmod` in `.memory/knowledge/` returned Permission denied, because the repo is mounted from the Mac host.

### When to revise a pruning trigger
- If a fresh session acts on a stale next action or an outdated decision, shorten the review interval or add a check at that event.
- If the 90-day review keeps finding nothing to change, lengthen it.
- When GIMPL moves past Feature 1 into many parallel features, review per feature merge instead of on a fixed calendar.

## Data Classification
Before writing anything to a memory file, classify it:
- **Public** — Safe to commit to the repo and share broadly. Most project decisions and coding standards fall here.
- **Internal** — Safe within the team but not for public repos. Store in a non-committed volume or .gitignore the containing folder.
- **Confidential** — Sensitive business data. Do not store in agent memory. Retrieve from secure systems on demand.
- **Secret** — Credentials, tokens, API keys, PII. Must never appear in any memory file. If the agent encounters a secret during a run, use it for the immediate task only and explicitly do not write it to any memory layer. Reference the environment variable name instead.

GIMPL note: .memory/ is committed (decision-002). Entries labeled Internal in GIMPL contain only project design context with no Confidential or Secret content, so committing them is accepted for this repo. Anything that would be Internal in the stricter sense above does not go in .memory/.

### Guardrails
A pre-commit hook at .git/hooks/pre-commit scans staged files under .memory/ for common credential patterns (sk-, password=, secret=, token=, api_key=, apikey=, case insensitive) before each commit. If a pattern is found, the commit is blocked and the file and pattern are printed. The hook is local only: .git/hooks/ is not committed or cloned, so a fresh clone must reinstall it. Tested 2026-11-06: it blocked .memory/test-secret.txt containing password=test123.

## Allocation decision table

| Information | Where it goes | Why |
|---|---|---|
| Why Feature 1 uses per-tic golden traces (decision-001) | Project memory | Reasoning the repo can't show; may be revisited |
| Where `.memory/` lives and how it merges (decision-002) | Project memory | Project decision with a review date |
| Current Feature 1 status and next action | Project memory | Changes every session |
| "Preserve original C behavior" and the other coding standards | Knowledge file | Stable rule; human-controlled |
| How to run the demo checks | Skill | A procedure (how), not memory (why) |
| wad sha256 and DEMO1 4227-tic expectation | Repo (`scripts/`, docs) | Already preserved in code and docs |
| Raw traces and session transcripts | Repo artifacts or not stored | Evidence, not memory; too large to load |
| Slack and Gmail credentials, tokens | Never stored | Secrets stay outside GIMPL |
| One-off session permissions | Not stored | Must not become standing authorization |
| Large external specs (future) | Indexed reference | Looked up on demand, not loaded at startup |
| "Reference traces need human approval" | Knowledge file (coding standard 4), decision-001 points to it | Could have stayed only in project memory as part of decision-001. Kept in knowledge so it is read-only and outlives the decision if decision-001 is superseded. Tradeoff: the agent cannot relax it even when a task seems to need it, so it must stop and ask, which adds a human step to every trace change. |

## Alternatives considered

### Put everything in CLAUDE.md
This would give every session one place to read, but mix stable rules with changing status and lengthy reference material. It would become harder to maintain and load unnecessary information every session. Instead, keep standing rules separate from evolving project memory and on-demand references.

### Rely only on the repository and session history
This avoids maintaining separate memory, but our activation showed its limitation: a fresh session recovered the implementation status and documented decisions, but could not reliably recover their rationale or deferred alternatives. Instead, preserve that missing reasoning in project memory and check it against the repository when resuming.
