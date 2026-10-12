# Parallel Agent Session Tasks

Two tasks run in parallel on GIMPL (Chocolate Heretic). Neither one changes game source, and their write scopes are separate files in separate folders, so the branches should merge without conflicts.

Why these two are safe to run side by side:
- Session A only reads C source and writes one new Markdown file under `docs/port-specs/`.
- Session B only writes one new script under `scripts/` and one new results file under `docs/smoke_tests/`.
- Neither write list includes a file the other session writes, and both sessions are barred from the shared files listed below.

Shared files excluded from BOTH write scopes, and why:
- `src/**` (all game and engine source). The demo check is only trustworthy if no session changes the code it measures, and the stay-C fence (renderer `r_*`, `z_zone`, `p_tick.c`, `d_net`, `s_sound`, `p_saveg`, `p_setup.c`, `src/m_fixed.c`) lives here.
- `Dockerfile`, `docker-entrypoint.sh`, `settings.json`, `statusline.sh`, `setup.md`. These define the sandbox both sessions run in.
- `.gitignore`, `configure.ac`, `Makefile.am`, `CMakeLists.txt`. Build and ignore rules are shared by every branch.
- `wads/` (the Blasphemer wad). It is the test data the demo check depends on. An agent that changes it could make a broken build look like it passes.
- `docs/smoke_tests/agent-summary.md` (the 1.1 evidence) and this `session_tasks.md` (the scope definition, edited only by me).

## Setup Verification

Why the isolation is scoped this way: each session gets its own worktree on its own branch, and each container mounts only that worktree at `/workspace`. If both agents shared one directory, Session B's build output and Session A's spec would land in the same working tree, one agent could overwrite or "clean up" the other's files mid-run, and `git status` could no longer tell me which agent changed what, so I couldn't review or merge each session on its own. Both containers share only the `claude-auth` volume for login, never my home directory.

`git worktree list` (before the sessions):
```
/home/george/Documents/agentic-engineer-course/capstone/gimpl         601ed78a [master]
/home/george/Documents/agentic-engineer-course/capstone/gimpl-agent-a 601ed78a [feature/port-spec-givebody-givearmor]
/home/george/Documents/agentic-engineer-course/capstone/gimpl-agent-b 601ed78a [feature/demo1-check-script]
```

`git branch` in each worktree (`*` marks the checked-out branch):
```
gimpl-agent-a: * feature/port-spec-givebody-givearmor
gimpl-agent-b: * feature/demo1-check-script
```

`ls /workspace` in each container: both show the full project tree and `session_tasks.md`. Only Session B's container shows `wads/`, because I copied the gitignored wad into that worktree alone, which confirms each container is mounted to a different host directory.

Launch command (run from inside each worktree):
```
docker run -it --rm -v "${PWD}:/workspace" -v claude-auth:/claude-auth gimpl
```

## Session A

Branch name: feature/port-spec-givebody-givearmor
Worktree directory: ../gimpl-agent-a
Task: Write a port spec for `P_GiveBody` and `P_GiveArmor` in `src/heretic/p_inter.c`, two small functions planned for a later port. For each function, document its C signature, what it returns and when, every `player_t` field and global it reads or writes, the constants it depends on (for example the max health and armor values), and every call site in `src/heretic` with file and line number, including which pickups trigger it.
Files or folders the agent may write to: `docs/port-specs/p_inter-givebody-givearmor.md` (new file, the only write)
Files or folders the agent may read but not write to: `src/heretic/p_inter.c`, `src/heretic/doomdef.h`, `src/heretic/p_local.h`, `src/heretic/info.h`, and any other file under `src/` it needs to trace a type or constant
Commands the agent may run: `ls`, `cat`, `grep`, `rg`, `wc`, `head`, `sed -n` (read-only commands only; no build, no git, no edits under `src/`)
Definition of done: `docs/port-specs/p_inter-givebody-givearmor.md` exists and contains, for both functions, the exact C signature, the return-value rules, a table of every field read and every field written, the constants used with their values and where they are defined, and a list of call sites with file and line numbers that I can spot-check against `p_inter.c`. `git status` in the worktree shows that file as the only change.

### Results

Merge decision: Merged
Reason: The spec is correct and useful groundwork for a later port. I spot-checked every call-site line number (p_inter.c:267, 297, 570, 577, 584; p_user.c:933, 939; p_pspr.c:1812) and the MAXHEALTH/MAXCHICKENHEALTH values in p_local.h:36-37 against source, and all matched. It also caught real details a port must keep: P_GiveArmor compares points but not armor type, and one call site is dead code. `git status` showed only the one allowed file. Drift: I interrupted the session when it said it was "fixing" line references, worried it was editing C; it was only correcting its own spec file and src/ was untouched. It did use `sed -i`, `python3` and `awk`, which were not on its read-only command list, so the next scope will either allow an editor command for its own output file or forbid those explicitly.
Commits on this branch:
9723106c Add port spec for P_GiveBody and P_GiveArmor

## Session B

Branch name: feature/demo1-check-script
Worktree directory: ../gimpl-agent-b
Task: Write a repeatable DEMO1 check script. It verifies the wad's sha256 before playing, runs the headless DEMO1 timedemo, and passes only if the game reports the expected 4227 gametics. The game normally exits with code 255 after a timedemo, so the script must judge the result from the `timed` line, not the game's exit code. Then run it and record the results.
Files or folders the agent may write to: `scripts/demo1-check.sh` (new file), `docs/smoke_tests/demo1-check.md` (new file; the original scope said `docs/smoke-tests/`, corrected after the run, see Results). The build also writes object files and `src/chocolate-heretic`, which are gitignored build outputs, not source edits.
Files or folders the agent may read but not write to: `setup.md`, `docs/smoke_tests/agent-summary.md`, `wads/blasphem.wad`, `src/` (to find the built binary), `autogen.sh`, `Makefile.am`
Commands the agent may run: `./autogen.sh`, `make -j$(nproc)`, `sha256sum`, `chmod +x scripts/demo1-check.sh`, `bash scripts/demo1-check.sh`, `src/chocolate-heretic -iwad wads/blasphem.wad -timedemo demo1 -nodraw -nosound`, `ls`, `cat`, `grep`
Definition of done: `scripts/demo1-check.sh` exists and is executable. It exits non-zero with a clear message if `wads/blasphem.wad` is missing or its sha256 is not `e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`. On the real build it prints PASS with the exact `timed` line and exits 0. Run with `EXPECTED_TICS=1` it prints FAIL and exits non-zero. `docs/smoke_tests/demo1-check.md` contains the pasted output and exit codes of both runs. `git status` in the worktree shows only those two new files.

### Results

Merge decision: Merged
Reason: The script does what the definition of done asks. Its normal run printed PASS with exit 0 and the EXPECTED_TICS=1 run printed FAIL with exit 1, and I reran it myself on the host before merging and got `timed 4227 gametics` and PASS. `git status` showed only the two allowed new files; the build output it generated is gitignored. Two issues found in review: (1) my scope named `docs/smoke-tests/` but the repo's folder is `docs/smoke_tests/`; the agent followed the scope as written and flagged the mismatch, and I moved the results file into the existing folder before committing. (2) On a host with a display the game opened a window that blocked the script, because only the container sets SDL to headless. I fixed this myself after the merge with a follow-up commit on master that exports the SDL dummy drivers inside the script.
Commits on this branch:
49362a89 Add DEMO1 check script with wad integrity check
