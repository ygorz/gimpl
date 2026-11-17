# Coding Standards

Last reviewed: 2026-11-05
Maintained by: George Gorzhiyev

These standards apply to all code in this project. The agent should consult this file before writing or reviewing any code. These rules are set by humans and the agent should never modify this file.

1. Preserve original C behavior exactly. A Rust port must reproduce the original C function's behavior, quirks included, before any improvement.
2. Port one function at a time. Each port has its own port spec and is verified on its own.
3. Demos decide correctness. A port is complete only when the blasphem.wad sha256 check and the demo checks pass (DEMO1 at 4227 tics).
4. Reference traces require human approval. Never create, regenerate, or edit golden traces or their manifest without explicit human approval.
5. Keep src/ edits narrow. Change C source only when the current task authorizes it (such as the opt-in -tichash hook), and never alter normal gameplay.
6. No secrets in the repo. Never commit credentials, tokens, or private data.
7. Reread saved artifacts. After saving a file, reread it for stale or contradictory claims before treating it as complete.
8. Never modify file permissions in .memory/knowledge/ without explicit human instruction.
