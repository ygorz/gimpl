#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block credentials from being written to .memory/.

Registered in .claude/settings.json for Write|Edit|MultiEdit. Reads the hook
JSON on stdin. If the target file is inside a .memory/ directory, scans the
new content (content, new_string, edits[].new_string). On a match, exits 2
with a message on stderr, which Claude Code shows to Claude and blocks the
tool call. Keep the patterns in sync with scripts/hooks/pre-commit.
"""
import json
import re
import sys
from pathlib import PurePath

PATTERNS = [
    ("sk- key", re.compile(r"sk-[A-Za-z0-9_-]{8,}")),
    ("keyword followed by : or = and a value",
     re.compile(r"(?i)(?<![A-Za-z0-9_])(api_key|apikey|token|secret|password|passwd)"
                r"[\"']?\s*[:=]\s*[\"']?[^\s\"']+")),
    ("credential value in an ALL-CAPS name",
     re.compile(r"(?<![A-Za-z0-9_])[A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD)(_[A-Z0-9]+)+"
                r"(?![A-Za-z0-9_])")),
    ("AWS access key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("private key block", re.compile(r"BEGIN [A-Z0-9 ]*PRIVATE KEY")),
]


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input") or {}
    except Exception as e:
        block(f"memory-secret-guard: could not parse hook input ({e}); "
              "blocking to be safe. Stop and tell George.")

    path = tool_input.get("file_path") or ""
    if ".memory" not in PurePath(path).parts:
        sys.exit(0)

    texts = [tool_input.get("content"), tool_input.get("new_string")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            texts.append(edit.get("new_string"))

    for text in texts:
        if not isinstance(text, str):
            continue
        for name, pattern in PATTERNS:
            if pattern.search(text):
                block(
                    f"BLOCKED by memory-secret-guard: write to {path} matches "
                    f"pattern '{name}' ({pattern.pattern}). Credentials must never "
                    "be stored in .memory/. Record only the env var name that holds "
                    "the credential (for example 'read from GIMPL_ARCHIVE_TOKEN'). "
                    "Do not retry through Bash or any other route; stop and tell George."
                )
    sys.exit(0)


if __name__ == "__main__":
    main()
