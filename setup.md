# GIMPL agent sandbox setup

This note explains how to run a coding agent safely on GIMPL - (G)eorge's Re(impl)ementation, a fork of Chocolate Doom where the work will be done on Chocolate Heretic (`src/heretic`) with Blasphemer 0.1.8 as the game data. It is the baseline container setup for the rest of the course and will change when the agent has a real project need, for example adding Rust when the first port starts.

## What the inspection found

- **Local services:** none. Chocolate Heretic is a single program. It needs no database, server, or background service.
- **Environment variables and credentials:** the repo references none. The only credential in the setup is the Claude Code login, and it lives in the `claude-auth` volume.
- **Smallest safe mount:** the `gimpl` repo folder. It holds the source, the build output, and `wads/blasphem.wad` (gitignored).
- **Network:** the game, the build, and the demo check need no network. Only Claude Code needs it, to reach its API.
- **Commands the repo defines:** `./autogen.sh && make` to build. Demo playback with `-timedemo` is the existing check.
- **Tools the container needs:** a C toolchain with autotools, the SDL2 libraries, git, and Node.js for Claude Code.



## Build the image

From the `gimpl` folder:

```sh
sudo docker build -t gimpl .
```



## Run the container

Agent sessions (network on, so Claude Code can reach its API):

```sh
sudo docker run -it --rm -v "$PWD:/workspace" -v claude-auth:/claude-auth gimpl
```

Offline runs and the egress check (no network at all):

```sh
sudo docker run -it --rm --network none -v "$PWD:/workspace" gimpl
```

- **Mounted path:** the host `gimpl` folder at `/workspace`, plus the named volume `claude-auth` at `/claude-auth`. Nothing else from the host is mounted. `~/.claude` is never mounted.
- **Network mode:** default bridge for agent sessions, `none` for offline runs and the egress check.

After any session that writes files, run this on the host from inside `gimpl`:

```sh
sudo chown -R "$USER:$USER" .
```

The container runs as root, so every file it creates or rebuilds in `/workspace` (build output, `agent-summary.md`, anything the agent writes) lands on the host owned by root instead of my user. Without this step, my editor and normal git commands can't edit, delete, or commit those files without `sudo`, and the next host-side `make` can fail on root-owned build files. The command hands ownership of everything in the folder (`-R` means every file and subfolder) back to my user. It's safe to run even after a session that only read files.

## Boundary checks

Inside the container:

```
gimpl:/workspace# ls /workspace
AUTHORS             Makefile         README.Strife.md  autotools        configure             pkg            statusline.sh
CMakeLists.txt      Makefile.am      README.md         check-extern.sh  configure.ac          quickcheck     textscreen
CODE_OF_CONDUCT.md  Makefile.in      RELEASE_NOTES.md  cmake            data                  rpm.spec       vcpkg.json
COPYING.md          NEWS.md          TODO.md           config.h         docker-entrypoint.sh  rpm.spec.in    wads
ChangeLog           NOT-BUGS.md      aclocal.m4        config.hin       man                   settings.json  win32
Dockerfile          PHILOSOPHY.md    autogen.sh        config.log       opl                   src
HACKING.md          README.Music.md  autom4te.cache    config.status    pcsound               stamp-h1
```

My home folder is not visible (empty output):

```
gimpl:/workspace# ls /home
```

No SSH keys inside the container:

```
gimpl:/workspace# ls /root/.ssh
ls: cannot access '/root/.ssh': No such file or directory
```

Network egress check, in the `--network none` container:

```
gimpl:/workspace# curl https://example.com
curl: (6) Could not resolve host: example.com
```

Persistence check. Inside a container I ran `echo test > /tmp/scratch.txt` and `echo test > /workspace/persist-check.txt`, then exited.

On the host:

```
$ cat persist-check.txt
test
```

In a fresh container:

```
gimpl:/workspace# ls /tmp/scratch.txt
ls: cannot access '/tmp/scratch.txt': No such file or directory
```



## Smoke test

Prompt given to Claude Code inside the networked container:

> Rebuild Chocolate Heretic with `make clean && ./autogen.sh && make -j$(nproc)`. Then run `src/chocolate-heretic -iwad wads/blasphem.wad -timedemo demo1 -nodraw -nosound 2>&1 | grep timed`. Exit code 255 is normal for a timedemo. Then run `git status --short`. Write a short summary to `/workspace/agent-summary.md` that includes the commands you ran, whether the build passed, the exact timed line, and the full `git status --short` output. Do not edit any source files.

Agent output:

```
The build passed and the timedemo ran. I wrote the summary to /workspace/agent-summary.md.

- Build: make clean && ./autogen.sh && make -j$(nproc) exited with 0.
- Timedemo: it exited with 255, which you said is normal. The timed line was:
  timed 4227 gametics in 139 realtics (1064.352539 fps)
- git status --short:
?? Dockerfile
?? docker-entrypoint.sh
?? settings.json
?? statusline.sh

I didn't edit any source files. I ran git status before writing the summary, so agent-summary.md isn't in that output. It will show up as a new untracked file if you run git status now.
```

After exiting, on the host, `agent-summary.md` was in `gimpl` and owned by root, which shows the container wrote it through the mount. `git status --short` on the host showed only the new Docker files and `agent-summary.md`, with no source files modified.

Two setup gaps came out of earlier smoke test runs and were fixed before this one:

- The game prints its `timed` line through its error output, which comes out before the buffered startup messages, so the agent first misread a successful run as a failure. Piping through `grep timed` makes the result unambiguous.
- git refused to run in `/workspace` because the files belong to my host user while git in the container runs as root. I added `git config --global --add safe.directory /workspace` to the Dockerfile so the agent can check its own changes.



## Security decisions

**1. Why did you mount only this folder?**

I mounted only the `gimpl` repo because everything the agent needs is inside it: the Heretic engine source code, the build output, and the Blasphemer wad in `wads/`. Nothing outside it is needed to build or run the game. My home folder holds things an agent should never see, like `~/.ssh`, `~/.claude` (which I use for Claude Code for personal projects), browser data, and my other repos. If I had mounted my home folder, a misbehaving agent or a malicious instruction hidden in a file could read my SSH keys and push to any of my GitHub repos, or change my personal Claude settings. The check above shows `/home` is empty and `/root/.ssh` doesn't exist inside the container.

**2. What did you choose to keep ephemeral?**

Everything inside the container that isn't a mount is thrown away on exit. That includes `/tmp`, the shell history, any packages the agent installs while running, and Claude Code's session files in `/root/.claude` apart from the saved login. That way, if the agent installs a tool or changes system files mid-session, the next session starts from the clean image instead of inheriting it. The `/tmp` check above confirms scratch files don't survive a restart.

**3. What did you choose to persist?**

Two things persist. The `/workspace` bind mount keeps the repo, the build output, and anything the agent writes there, like `agent-summary.md`, because that's the work I want to review and commit on the host. The `claude-auth` named volume keeps only the Claude Code credential file, so I don't have to sign in every session. Keeping the login in its own volume, instead of mounting my host `~/.claude`, means the agent can never touch my personal Claude config or credentials, and the course login stays separate.

**4. What dependencies did you include in your extended Docker image?**

Each tool is there for a specific GIMPL need:

- `gcc`, `make`, `autoconf`, `automake`, `libtool`, `pkg-config` to run the project's own build (`./autogen.sh && make`).
- `libsdl2-dev`, `libsdl2-mixer-dev`, `libsdl2-net-dev`, the SDL2 libraries Chocolate Heretic links against.
- `git` so the agent can check its changes with `git status` and `git diff`, plus the `safe.directory` setting that lets it run on the mounted repo.
- `curl` and `ca-certificates` for HTTPS, which Claude Code needs, and for the egress check.
- `nodejs` and `npm` to install and run Claude Code.
- `bash` and `procps` so the agent has a normal shell and can check for a stuck process.

I set `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` so the game always runs headless, since the container has no display or sound device. I removed OpenCode, ngrok, nano, and the course's Python packages (streamlit, pandas, flask, the Slack and Google libraries, and others), because nothing in GIMPL uses them. Rust is deliberately not installed yet. I'll add it when the first port to Rust starts.

**5. What did your smoke test prove?**

The smoke test proved the agent can do real work on the project inside the boundaries. It rebuilt Chocolate Heretic from clean with only the tools in the image, and it played Blasphemer's DEMO1 to the expected 4,227 tics headless, using the wad from the mounted folder. It also confirmed the filesystem boundary from both sides. `agent-summary.md` appeared on the host owned by root, so the container's writes land in `/workspace` and persist. And `git status` showed no source files changed and nothing written outside the repo. The earlier failed runs were useful too because they exposed the git ownership gap, which I fixed in the Dockerfile.

**6. What risks remain?**

- **Open network during agent sessions.** Claude Code needs the internet, so in agent sessions the container can reach any host. A prompt injection could make the agent download and run a script, or send repo contents somewhere. Mitigation: run builds and demo checks with `--network none`, which works because the game needs no network. Later, I'd restrict agent sessions to an allowlist that only reaches the Claude API.
- **The agent can change its own test data.** The wad and demos live in the writable `/workspace`, so a careless or misbehaving agent could alter `blasphem.wad` and make a broken port look like it passes. Mitigation: check the wad's sha256 (`e9ed3f53...`) before every demo run, as part of the demo comparison check in Feature 1.
- **Root inside the container.** The agent runs as root and can write anything in `/workspace`, including `.git/hooks` and the Dockerfile itself. Mitigation: review `git status` and `git diff` after every session, commit only from the host, and look out for changes to `.git/` or the Dockerfile.

