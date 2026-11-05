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

### Belongs here
- An index pointing to port specs, including the P_GiveArtifact spec.
- Links to demo-check documentation and recorded test evidence.
- Links to context summaries and handoffs, labeled by session or feature.
- A link to the iteration log for historical decisions and results.

### Does not belong here
- Copies of whole documents inside the index: link to the authoritative artifact instead.
- Unlabeled old handoffs presented as current instructions: historical material must not override current rules.

### Scope
GIMPL reference material. Each index entry states its topic, when to consult it, and whether it is current or historical.

### Write permissions
The agent may maintain the index and edit task-authorized documents. Being indexed does not grant permission to edit a document or change its rules.

### Pruning policy
Check links when documents move or features finish. Update or remove broken entries, label superseded documents, and retain useful historical evidence without loading it into every session.

## Allocation decision table

## Alternatives considered

### Put everything in CLAUDE.md
This would give every session one place to read, but mix stable rules with changing status and lengthy reference material. It would become harder to maintain and load unnecessary information every session. Instead, keep standing rules separate from evolving project memory and on-demand references.

### Rely only on the repository and session history
This avoids maintaining separate memory, but our activation showed its limitation: a fresh session recovered the implementation status and documented decisions, but could not reliably recover their rationale or deferred alternatives. Instead, preserve that missing reasoning in project memory and check it against the repository when resuming.
