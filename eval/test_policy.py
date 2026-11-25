"""Policy test suite: the governance policy and its enforcement must agree.

Run from the repository root:  python3 -m pytest eval/test_policy.py -v

docs/governance-policy.md is the written policy. These tests read it, read
every artifact that enforces it, and fail wherever the two say different
things, in either direction:

- the storage and retrieval allow-lists (Layer 2, MCP servers);
- the _authorize() guard on every storage and retrieval operation;
- the agent files in .claude/agents/ (tool grants, skill preloads and the
  role each agent's own MCP server is started with);
- the case block in scripts/run-agent.sh (Layer 1, container mounts);
- .github/workflows/ci.yml, against its design in docs/ci-step-design.md
  (gates that cannot be bypassed, an advisory review that cannot block, an
  audit trail that always runs, one step-scoped secret).

Role names, grants and ceilings come from the policy document, not from this
file, so a new role is covered as soon as its policy entry exists. When a
check fails, the message names the role and shows both sides. Decide which
side is right and fix that side only.

The hooks have their own tests in eval/tests/. Nothing here needs Docker,
the network, a secret or a running MCP server: the servers are read as
source, and run-agent.sh runs in its dry-run mode, which prints the docker
command instead of running it. The CI checks read ci.yml with PyYAML,
pinned in requirements-ci.txt and installed in the gimpl image.
"""

import ast
import json
import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(ROOT, "docs", "governance-policy.md")
AGENTS_DIR = os.path.join(ROOT, ".claude", "agents")
SKILLS_DIR = os.path.join(ROOT, ".claude", "skills")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
MCP_JSON = os.path.join(ROOT, ".mcp.json")
RUN_AGENT = os.path.join(ROOT, "scripts", "run-agent.sh")
SERVERS = {
    "storage": os.path.join(ROOT, "mcp", "storage", "server.py"),
    "retrieval": os.path.join(ROOT, "mcp", "retrieval", "server.py"),
}
ALLOW_LISTS = {
    "storage": os.path.join(ROOT, "mcp", "storage", "allow-list.json"),
    "retrieval": os.path.join(ROOT, "mcp", "retrieval", "allow-list.json"),
}

# The orchestrator is the main Claude Code session, not a subagent. The
# policy's skill section says so, and test_least_privilege_default_is_stated
# checks that sentence. Its skills are not preloaded, so its skill scope is
# checked differently.
MAIN_SESSION = "orchestrator"

DIMENSIONS = (
    "### MCP server and operation access",
    "### Skill activation scope",
    "### Data classification ceiling",
    "### Autonomy level",
)

# Container line wording -> what run-agent.sh must do.
WORKSPACE_MODES = {"read-write": "rw", "read-only": "ro"}
MEMORY_STATES = {"mounted": True, "omitted": False}


# --- Reading the policy document ------------------------------------------

def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _table_rows(section, heading):
    """Rows of the first markdown table after a heading, header row skipped."""
    start = section.index(heading)
    rows = []
    for line in section[start:].splitlines()[1:]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif rows or line.startswith("#"):
            break
    return rows[1:]


def _field(section, label):
    match = re.search(r"^\*\*" + re.escape(label) + r":\*\*\s*(.+?)\s*$", section, re.M)
    return match.group(1) if match else None


def load_policy():
    """The policy as data: {role: entry}, plus the document text."""
    text = _read(POLICY)
    roles = {}
    parts = re.split(r"^## Role: *(\S+) *$", text, flags=re.M)
    for name, body in zip(parts[1::2], parts[2::2]):
        body = re.split(r"^## ", body, flags=re.M)[0]
        entry = {"text": body}
        if all(d in body for d in DIMENSIONS):
            ops = _table_rows(body, DIMENSIONS[0])
            skills = _table_rows(body, DIMENSIONS[1])
            entry["operations"] = {r[0].strip("`"): {"server": r[1], "granted": r[2], "reason": r[3]}
                                   for r in ops if len(r) >= 4}
            entry["skills"] = {r[0].strip("`"): {"granted": r[1], "reason": r[2]}
                               for r in skills if len(r) >= 3}
        entry["ceiling"] = _field(body, "Maximum level")
        entry["autonomy"] = _field(body, "Level")
        entry["container"] = _field(body, "Container permissions")
        entry["defined_in"] = (_field(body, "Defined in") or "").strip("`")
        roles[name] = entry
    return text, roles


POLICY_TEXT, POLICY_ROLES = load_policy()
ROLES = sorted(POLICY_ROLES)


def _levels():
    """Classification levels, lowest first, as the policy lists them."""
    match = re.search(r"Classification levels, lowest to highest, are ([^.]+)\.", POLICY_TEXT)
    assert match, "the policy no longer states the classification levels, lowest to highest"
    return [w.strip("` ") for w in re.split(r",|\band\b", match.group(1)) if w.strip("` ")]


LEVELS = _levels()


def granted(role, kind):
    """The operations (kind='operations') or skills (kind='skills') the
    policy grants a role, as a set."""
    return {name for name, row in POLICY_ROLES[role].get(kind, {}).items() if row["granted"] == "YES"}


def policy_operations(server):
    """Every operation the policy lists for a server, from the role tables."""
    return {op for entry in POLICY_ROLES.values()
            for op, row in entry.get("operations", {}).items() if row["server"] == server}


# --- Reading the enforcement artifacts ------------------------------------

def _strip_comment(value):
    return re.sub(r"\s+#.*$", "", value).strip()


def load_agent(path):
    """Frontmatter of an agent file: name, tools, disallowedTools, skills
    (as lists) and mcpServers as {server: {env var: value}}. Reads only the
    simple YAML shapes the agent files use, so no YAML library is needed."""
    lines = _read(path).splitlines()
    assert lines and lines[0].strip() == "---", f"{path}: no frontmatter"
    end = lines.index("---", 1)
    fields, servers = {}, {}
    key, server = None, None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            key, _, value = line.partition(":")
            key, value = key.strip(), _strip_comment(value)
            server = None
            if value in ("", ">", "|", ">-", "|-"):
                fields[key] = [] if value == "" else ""
            else:
                fields[key] = [v.strip() for v in value.split(",")] if key in (
                    "tools", "disallowedTools", "skills") else value
            continue
        if key == "mcpServers":
            item = re.match(r"^\s*-\s*([\w-]+):\s*$", line)
            env = re.match(r"^\s+([A-Z][A-Z0-9_]*):\s*(.+?)\s*$", line)
            if item:
                server = item.group(1)
                servers[server] = {}
            elif env and server:
                servers[server][env.group(1)] = _strip_comment(env.group(2)).strip("\"'")
            continue
        item = re.match(r"^\s+-\s+(.+)$", line)
        if item and isinstance(fields.get(key), list):
            fields[key].append(_strip_comment(item.group(1)))
    fields["mcpServers"] = servers
    return fields


def project_skills():
    """Skill folders under .claude/skills/. Only the folder names are read,
    never a SKILL.md."""
    return sorted(d for d in os.listdir(SKILLS_DIR)
                  if not d.startswith(".") and os.path.isdir(os.path.join(SKILLS_DIR, d)))


def agent_files():
    return sorted(f[:-3] for f in os.listdir(AGENTS_DIR) if f.endswith(".md"))


def load_case_block():
    """{role: (workspace mode, memory mounted)} from run-agent.sh's case
    block, plus the role list the script prints for an unknown role."""
    script = _read(RUN_AGENT)
    block = re.search(r'^case "\$ROLE" in\n(.*?)^esac', script, re.M | re.S)
    assert block, "run-agent.sh has no 'case \"$ROLE\" in ... esac' block"
    branches = {}
    for pattern, body in re.findall(r"^\s*([\w|-]+)\)\n(.*?);;", block.group(1), re.M | re.S):
        mode = re.search(r'WORKSPACE_MODE="(\w+)"', body)
        memory = re.search(r"MOUNT_MEMORY=(\d)", body)
        for role in pattern.split("|"):
            branches[role] = (mode.group(1) if mode else None, memory.group(1) == "1" if memory else None)
    listed = re.search(r'echo "Roles: ([^"]+)"', block.group(1))
    return branches, (listed.group(1).split() if listed else [])


def dry_run(role):
    """Run run-agent.sh in dry-run mode, which prints the docker command."""
    env = {k: v for k, v in os.environ.items() if k not in ("AGENT_NETWORK", "AGENT_IMAGE")}
    env["RUN_AGENT_DRY_RUN"] = "1"
    return subprocess.run(["bash", RUN_AGENT, role], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=30)


def load_server(server):
    """Parsed source of an MCP server, and its tools: {name: function node}."""
    tree = ast.parse(_read(SERVERS[server]))
    tools = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
             and any(ast.unparse(d) in ("mcp.tool", "mcp.tool()") for d in node.decorator_list)}
    return tree, tools


def module_constant(tree, name):
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return node.value
    raise AssertionError(f"{name} is not defined at module level")


STORAGE_ALLOW = json.loads(_read(ALLOW_LISTS["storage"]))
RETRIEVAL_ALLOW = json.loads(_read(ALLOW_LISTS["retrieval"]))
AGENTS = {name: load_agent(os.path.join(AGENTS_DIR, name + ".md")) for name in agent_files()}
CASE_BRANCHES, CASE_LISTED = load_case_block()


def _agent(role):
    assert role in AGENTS, f"{role}: no agent file at .claude/agents/{role}.md"
    return AGENTS[role]


# --- The policy document itself -------------------------------------------

def test_policy_files_present():
    """Every governed file the policy names exists."""
    for path in [POLICY, RUN_AGENT, SETTINGS, *SERVERS.values(), *ALLOW_LISTS.values(),
                 os.path.join(ROOT, "eval", "red-team-prompts.md"),
                 os.path.join(ROOT, "eval", "red-team-results.md")]:
        assert os.path.isfile(path), f"missing governed file: {os.path.relpath(path, ROOT)}"


def test_least_privilege_default_is_stated():
    """The policy opens from deny-by-default, and names the main session."""
    assert "Every role starts with no access." in POLICY_TEXT
    assert "Any access not explicitly granted to a role is denied by default." in POLICY_TEXT
    assert f"The {MAIN_SESSION} is the main session" in POLICY_TEXT


@pytest.mark.parametrize("role", ROLES)
def test_role_entry_is_complete(role):
    """Each role has all four dimensions, a container line, a row for every
    operation and every skill, and a reason for every denial."""
    entry = POLICY_ROLES[role]
    missing = [d for d in DIMENSIONS if d not in entry["text"]]
    assert not missing, f"{role}: policy entry is missing {missing}"
    all_ops = policy_operations("storage") | policy_operations("retrieval")
    assert set(entry["operations"]) == all_ops, (
        f"{role}: operation rows {sorted(entry['operations'])} != operations in the policy {sorted(all_ops)}")
    skills = project_skills()
    assert sorted(entry["skills"]) == skills, (
        f"{role}: skill rows {sorted(entry['skills'])} != skills in .claude/skills/ {skills}")
    for kind in ("operations", "skills"):
        for name, row in entry[kind].items():
            assert row["granted"] in ("YES", "NO"), f"{role}: {name} must be YES or NO, not {row['granted']!r}"
            if row["granted"] == "NO":
                assert row["reason"], f"{role}: denial of {name} has no reason"
    assert entry["ceiling"] in LEVELS, f"{role}: ceiling {entry['ceiling']!r} is not one of {LEVELS}"
    assert entry["autonomy"] in ("low", "medium", "high"), f"{role}: autonomy {entry['autonomy']!r}"
    assert entry["container"], f"{role}: no '**Container permissions:**' line"


def test_roles_agree_across_artifacts():
    """The same roles appear in the policy, the agent files, run-agent.sh and
    the retrieval allow-list, and the storage allow-list names no other role."""
    stated = re.search(r"one entry for each of the (\d+) roles", POLICY_TEXT)
    assert stated and int(stated.group(1)) == len(ROLES), (
        f"policy says {stated.group(1) if stated else '?'} roles but has {len(ROLES)} entries: {ROLES}")
    assert agent_files() == ROLES, f".claude/agents/ {agent_files()} != policy roles {ROLES}"
    assert sorted(CASE_BRANCHES) == ROLES, f"run-agent.sh case block {sorted(CASE_BRANCHES)} != policy roles {ROLES}"
    assert sorted(CASE_LISTED) == ROLES, f"run-agent.sh 'Roles:' message {sorted(CASE_LISTED)} != policy roles {ROLES}"
    for op, grants in RETRIEVAL_ALLOW.items():
        assert sorted(grants) == ROLES, f"retrieval allow-list '{op}' covers {sorted(grants)}, policy roles are {ROLES}"
    for op, grants in STORAGE_ALLOW.items():
        unknown = set(grants) - set(ROLES)
        assert not unknown, f"storage allow-list '{op}' names roles with no policy entry: {sorted(unknown)}"


@pytest.mark.parametrize("role", ROLES)
def test_agent_file_matches_policy_entry(role):
    """The policy entry points at the agent file, and the file's name: field
    is the role."""
    entry = POLICY_ROLES[role]
    assert entry["defined_in"] == f".claude/agents/{role}.md", (
        f"{role}: 'Defined in' is {entry['defined_in']!r}, expected .claude/agents/{role}.md")
    assert _agent(role).get("name") == role, f"{role}: agent file name: is {_agent(role).get('name')!r}"


# --- Layer 2: storage server ----------------------------------------------

@pytest.mark.parametrize("operation", sorted(policy_operations("storage")))
def test_storage_allowlist_matches_policy(operation):
    """mcp/storage/allow-list.json grants each operation to exactly the roles
    the policy marks YES."""
    policy_side = sorted(r for r in ROLES if operation in granted(r, "operations"))
    allow_side = sorted(STORAGE_ALLOW.get(operation, ["(operation missing)"]))
    assert allow_side == policy_side, (
        f"storage '{operation}': allow-list grants {allow_side}, policy grants {policy_side}")


def test_storage_allowlist_has_no_unknown_operation():
    """The allow-list holds only operations the policy governs."""
    extra = set(STORAGE_ALLOW) - policy_operations("storage")
    assert not extra, f"storage allow-list has operations the policy does not list: {sorted(extra)}"


@pytest.mark.parametrize("role", ROLES)
def test_no_storage_overgrant(role):
    """The dangerous direction: no artifact gives a role a storage operation
    its policy entry denies, whether in the allow-list or as a tool in its
    agent file."""
    allowed = granted(role, "operations")
    in_allow_list = {op for op, roles in STORAGE_ALLOW.items() if role in roles}
    in_agent_file = {t.split("__", 2)[2] for t in _agent(role).get("tools", [])
                     if t.startswith("mcp__storage__")}
    assert in_allow_list <= allowed, (
        f"{role}: allow-list grants {sorted(in_allow_list - allowed)} that the policy denies")
    assert in_agent_file <= allowed, (
        f"{role}: agent file tools grant {sorted(in_agent_file - allowed)} that the policy denies")


def test_delete_entry_is_granted_to_no_role():
    """Removing a stored entry is an operator action, so no role holds it."""
    assert not [r for r in ROLES if "delete_entry" in granted(r, "operations")]
    assert STORAGE_ALLOW.get("delete_entry") == []


def test_storage_write_classifications_within_writer_ceilings():
    """The storage server refuses any write above the lowest ceiling among
    the roles allowed to write."""
    tree, _ = load_server("storage")
    writable = ast.literal_eval(module_constant(tree, "WRITE_CLASSIFICATIONS"))
    for role in STORAGE_ALLOW.get("write_entry", []):
        ceiling = LEVELS.index(POLICY_ROLES[role]["ceiling"])
        above = sorted(c for c in writable if LEVELS.index(c) > ceiling)
        assert not above, f"storage accepts {above} writes, above {role}'s ceiling {POLICY_ROLES[role]['ceiling']}"


# --- Layer 2: retrieval server --------------------------------------------

@pytest.mark.parametrize("role", ROLES)
def test_retrieval_allowlist_matches_policy(role):
    """mcp/retrieval/allow-list.json grants retrieve, with the policy's
    ceiling, to exactly the roles the policy marks YES; every other role
    carries a denial reason."""
    for op in sorted(policy_operations("retrieval")):
        grant = RETRIEVAL_ALLOW.get(op, {}).get(role)
        assert grant is not None, f"{role}: no '{op}' entry in the retrieval allow-list"
        policy_yes = op in granted(role, "operations")
        assert grant.get("granted") is policy_yes, (
            f"{role}: retrieval '{op}' granted={grant.get('granted')}, policy says {'YES' if policy_yes else 'NO'}")
        if policy_yes:
            assert grant.get("classification_ceiling") == POLICY_ROLES[role]["ceiling"], (
                f"{role}: allow-list ceiling {grant.get('classification_ceiling')!r}, "
                f"policy ceiling {POLICY_ROLES[role]['ceiling']!r}")
        else:
            assert grant.get("denial_reason"), f"{role}: retrieval denial has no denial_reason"


def test_retrieval_server_ceiling_defaults():
    """The retrieval server ranks classifications in the policy's order, and
    its fallback ceilings sit no higher than the highest ceiling any role holds."""
    tree, _ = load_server("retrieval")
    order = ast.literal_eval(module_constant(tree, "CLASSIFICATION_ORDER"))
    assert order == LEVELS, f"server order {order} != policy order {LEVELS}"
    top = max(LEVELS.index(POLICY_ROLES[r]["ceiling"]) for r in ROLES)
    default = ast.literal_eval(module_constant(tree, "DEFAULT_CEILING"))
    max_call = module_constant(tree, "MAX_CEILING")
    max_default = ast.literal_eval(max_call.args[1])
    for name, value in (("DEFAULT_CEILING", default), ("RETRIEVAL_MAX_CEILING default", max_default)):
        assert LEVELS.index(value) <= top, f"{name} is {value!r}, above every role's ceiling ({LEVELS[top]})"


# --- Layer 2: both servers ------------------------------------------------

@pytest.mark.parametrize("server", sorted(SERVERS))
def test_every_server_operation_is_guarded(server):
    """The server exposes exactly the operations the policy lists, each tool
    calls _authorize() with its own name before anything else, and the role
    comes from AGENT_ROLE and the grants from allow-list.json."""
    tree, tools = load_server(server)
    assert set(tools) == policy_operations(server), (
        f"{server} server tools {sorted(tools)} != policy operations {sorted(policy_operations(server))}")
    for name, node in tools.items():
        body = node.body[1:] if ast.get_docstring(node) else node.body
        calls = [n for n in ast.walk(body[0]) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "_authorize"]
        assert calls, f"{server}.{name}: first statement does not call _authorize()"
        assert ast.literal_eval(calls[0].args[0]) == name, (
            f"{server}.{name}: _authorize() is called for {ast.unparse(calls[0].args[0])}")
    source = _read(SERVERS[server])
    assert 'os.environ.get("AGENT_ROLE"' in source or 'os.getenv("AGENT_ROLE"' in source, (
        f"{server}: role is not read from AGENT_ROLE")
    assert '"allow-list.json"' in source, f"{server}: grants are not loaded from allow-list.json"


@pytest.mark.parametrize("role", ROLES)
def test_agent_file_mcp_tools_match_policy(role):
    """An agent file lists a storage or retrieval tool exactly when the
    policy grants it, blocks every denied one, and starts any server it
    declares with its own role in AGENT_ROLE (never another role's)."""
    agent = _agent(role)
    tools, blocked = set(agent.get("tools", [])), set(agent.get("disallowedTools", []))
    assert tools, f"{role}: agent file has no tools: list, so it would inherit every tool"
    for server in SERVERS:
        for op in sorted(policy_operations(server)):
            tool = f"mcp__{server}__{op}"
            if op in granted(role, "operations"):
                assert tool in tools, f"{role}: policy grants {op}, agent file tools do not list {tool}"
                assert tool not in blocked, f"{role}: policy grants {op}, agent file disallows {tool}"
            else:
                assert tool not in tools, f"{role}: policy denies {op}, agent file tools list {tool}"
    for server, env in agent["mcpServers"].items():
        assert env.get("AGENT_ROLE") == role, (
            f"{role}: its '{server}' server starts with AGENT_ROLE={env.get('AGENT_ROLE')!r}")
        ceiling = env.get("RETRIEVAL_MAX_CEILING")
        if ceiling:
            assert LEVELS.index(ceiling) <= LEVELS.index(POLICY_ROLES[role]["ceiling"]), (
                f"{role}: RETRIEVAL_MAX_CEILING={ceiling}, policy ceiling {POLICY_ROLES[role]['ceiling']}")
    needs = {s for s in SERVERS if any(op in granted(role, "operations") for op in policy_operations(s))}
    assert needs <= set(agent["mcpServers"]), (
        f"{role}: granted operations on {sorted(needs)} but the agent file declares {sorted(agent['mcpServers'])}")


def test_main_session_has_no_storage_or_retrieval_server():
    """.mcp.json gives the main session neither server, so storage and
    retrieval exist only inside the subagents the policy grants."""
    declared = set(json.loads(_read(MCP_JSON)).get("mcpServers", {}))
    assert not declared & set(SERVERS), f".mcp.json declares {sorted(declared & set(SERVERS))}"


# --- Skill activation scope -----------------------------------------------

@pytest.mark.parametrize("role", ROLES)
def test_skill_scope_matches_policy(role):
    """A subagent preloads exactly the skills its entry permits and has no
    Skill tool to load others. The main session holds the Skill tool, so the
    policy must permit it every project skill, since nothing narrower is
    enforced there."""
    permitted = granted(role, "skills")
    if role == MAIN_SESSION:
        deny = json.loads(_read(SETTINGS)).get("permissions", {}).get("deny", [])
        assert not [d for d in deny if d == "Skill" or d.startswith("Skill(")], (
            "settings.json denies the Skill tool, but the policy gives the main session both skills")
        everything = set(POLICY_ROLES[role]["skills"])
        assert permitted == everything, (
            f"{role}: policy denies {sorted(everything - permitted)}, but the main session's Skill tool "
            "can load any project skill; enforce the denial or correct the policy")
        return
    agent = _agent(role)
    preloaded = set(agent.get("skills", []))
    assert preloaded == permitted, (
        f"{role}: agent file preloads {sorted(preloaded)}, policy permits {sorted(permitted)}")
    assert "Skill" not in agent.get("tools", []), f"{role}: agent file grants the Skill tool"


# --- Layer 1: container ---------------------------------------------------

def _container_policy(role):
    line = POLICY_ROLES[role]["container"] or ""
    match = re.fullmatch(r"workspace (read-write|read-only), memory (mounted|omitted)", line)
    assert match, f"{role}: container line {line!r} is not 'workspace read-write|read-only, memory mounted|omitted'"
    return WORKSPACE_MODES[match.group(1)], MEMORY_STATES[match.group(2)]


@pytest.mark.parametrize("role", ROLES)
def test_container_workspace_matches_policy(role):
    """run-agent.sh's case branch for the role sets the workspace mode and
    the memory mount its container line states, and the docker command it
    builds does the same."""
    mode, memory = _container_policy(role)
    assert role in CASE_BRANCHES, f"{role}: no branch in run-agent.sh's case block"
    assert CASE_BRANCHES[role] == (mode, memory), (
        f"{role}: run-agent.sh sets workspace={CASE_BRANCHES[role][0]}, memory mounted={CASE_BRANCHES[role][1]}; "
        f"policy says workspace={mode}, memory mounted={memory}")
    result = dry_run(role)
    assert result.returncode == 0, f"{role}: dry run failed: {result.stderr.strip()}"
    command = result.stdout
    assert f":/workspace:{mode} " in command, f"{role}: docker command does not mount the workspace {mode}: {command}"
    hides_memory = "type=tmpfs,destination=/workspace/.memory" in command
    assert hides_memory is not memory, (
        f"{role}: memory {'hidden' if hides_memory else 'visible'} in the docker command, policy says "
        f"{'mounted' if memory else 'omitted'}")
    assert f"AGENT_ROLE={role} " in command, f"{role}: docker command does not set AGENT_ROLE={role}"


def test_unknown_role_cannot_launch():
    """A role with no policy entry gets no container."""
    result = dry_run("no-such-role")
    assert result.returncode != 0
    assert "docker" not in result.stdout
    assert "no policy entry" in result.stderr


# --- CI pipeline: .github/workflows/ci.yml --------------------------------
#
# docs/ci-step-design.md is the written design of the pipeline, the way
# docs/governance-policy.md is the written policy for the agents. Which jobs
# gate is read from that document; these tests fail where ci.yml would let a
# gate be bypassed or a secret leak, or where the two disagree.

CI_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")
CI_DESIGN = os.path.join(ROOT, "docs", "ci-step-design.md")

# The policy gate and the eval gate are permanent gates: the design may add
# gates but never demote these two.
PERMANENT_GATES = {"policy-gate", "eval-gate"}
CLASSIFIER = "change-type-check"
AUDIT_JOB = "audit-trail"
REVIEW_JOB = "agent-review"
REVIEWER_SECRET = "CI_REVIEWER_OPENROUTER_KEY"
REVIEWER_STEP = "Run advisory reviewer"

# Shapes of real API keys and tokens. Built from parts so this file never
# matches its own scan.
KEY_SHAPES = re.compile("|".join([
    "sk-" + r"or-v1-[A-Za-z0-9]{16,}",
    "sk-" + r"ant-[A-Za-z0-9_-]{16,}",
    "gh" + r"[pousr]_[A-Za-z0-9]{30,}",
    "github" + r"_pat_[A-Za-z0-9_]{30,}",
]))


def load_workflow():
    """ci.yml as data. PyYAML is pinned in requirements-ci.txt and installed
    in the gimpl image; the import is here so a missing library fails only
    these tests, with a clear message."""
    import yaml
    with open(CI_WORKFLOW, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    # YAML 1.1 reads the bare key `on` as the boolean True.
    if True in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


def load_ci_design():
    """{job key: classification} from the '## Step: ... (`job-key`)' sections."""
    text = _read(CI_DESIGN)
    design = {}
    parts = re.split(r"^## Step: .*\(`([a-z0-9-]+)`\)\s*$", text, flags=re.M)
    for key, body in zip(parts[1::2], parts[2::2]):
        body = re.split(r"^## ", body, flags=re.M)[0]
        match = re.search(r"^- \*\*Classification:\*\*\s*(.+)$", body, re.M)
        design[key] = match.group(1).strip() if match else None
    return design


def _steps_text(job):
    return "\n".join(str(step.get("run", "")) + " " + str(step.get("uses", ""))
                     for step in job.get("steps", []))


def _needs(job):
    needs = job.get("needs", [])
    return {needs} if isinstance(needs, str) else set(needs)


def _gating_jobs():
    return {key for key, cls in load_ci_design().items() if cls and cls.startswith("gating")}


def test_ci_workflow_and_design_present():
    for path in (CI_WORKFLOW, CI_DESIGN):
        assert os.path.isfile(path), f"missing {os.path.relpath(path, ROOT)}"
    assert load_workflow().get("jobs"), "ci.yml defines no jobs"


def test_ci_triggers_have_no_path_filter():
    """A paths: filter skips the whole workflow, required gates included."""
    triggers = load_workflow()["on"]
    assert "pull_request" in triggers, "ci.yml does not run on pull requests"
    assert "push" in triggers, "ci.yml does not run on push"
    for event, config in triggers.items():
        config = config or {}
        for key in ("paths", "paths-ignore"):
            assert key not in config, f"ci.yml '{event}' trigger has a {key} filter"


def test_ci_design_covers_every_job():
    """Every job in ci.yml has a design section, and every designed job exists."""
    jobs = set(load_workflow()["jobs"])
    design = load_ci_design()
    assert jobs == set(design), (
        f"ci.yml jobs without a design section: {sorted(jobs - set(design))}; "
        f"designed jobs missing from ci.yml: {sorted(set(design) - jobs)}")
    missing = sorted(key for key, cls in design.items() if not cls)
    assert not missing, f"design sections with no Classification line: {missing}"


def test_permanent_gates_stay_gating():
    gating = _gating_jobs()
    assert PERMANENT_GATES <= gating, (
        f"docs/ci-step-design.md no longer classifies {sorted(PERMANENT_GATES - gating)} as gating")


def _assert_gate_cannot_be_bypassed(key):
    jobs = load_workflow()["jobs"]
    assert key in jobs, f"gating job {key} is missing from ci.yml"
    job = jobs[key]
    assert job.get("continue-on-error") in (None, False), f"{key}: continue-on-error makes the gate advisory"
    assert "if" not in job, f"{key}: a job-level if: lets the gate report 'skipped' instead of a result"
    for step in job.get("steps", []):
        assert step.get("continue-on-error") in (None, False), (
            f"{key}: step {step.get('name') or step.get('uses')!r} has continue-on-error")


@pytest.mark.parametrize("job_key", sorted(PERMANENT_GATES))
def test_gating_job_cannot_be_bypassed(job_key):
    """A gate blocks only if it always reports a real result: no
    continue-on-error (job or step) and no job-level if:, since a skipped
    job satisfies a required status check."""
    _assert_gate_cannot_be_bypassed(job_key)


def test_every_designed_gate_cannot_be_bypassed():
    """Gates the design adds later get the same check."""
    for key in sorted(_gating_jobs() - PERMANENT_GATES):
        _assert_gate_cannot_be_bypassed(key)


def test_policy_gate_runs_this_suite():
    job = load_workflow()["jobs"]["policy-gate"]
    assert "eval/test_policy.py" in _steps_text(job), "policy-gate does not run eval/test_policy.py"
    assert "--json-report" in _steps_text(job), "policy-gate does not write a JSON report"


def test_eval_gate_follows_the_classifier():
    jobs = load_workflow()["jobs"]
    job = jobs["eval-gate"]
    assert {CLASSIFIER, "policy-gate"} <= _needs(job), "eval-gate must need change-type-check and policy-gate"
    conditions = " ".join(str(step.get("if", "")) for step in job.get("steps", []))
    assert f"needs.{CLASSIFIER}.outputs.requires-eval" in conditions, (
        "eval-gate's steps do not read the classifier's requires-eval output")
    text = _steps_text(job)
    assert "scripts/run-eval-gate.py --reports /reports" in text, "eval-gate does not run the harness"
    assert "--not-triggered" in text, "eval-gate records no not_triggered state when the harness is skipped"


def test_classifier_flags_cover_the_enforcement_files():
    """Every file this suite reads as enforcement sets requires-eval, so a
    change to it also runs the harness. A README change does not."""
    job = load_workflow()["jobs"][CLASSIFIER]
    outputs = job.get("outputs", {})
    for flag in ("changed-files", "requires-eval", "touches-policy"):
        assert flag in outputs, f"change-type-check has no {flag} output"
    match = re.search(r"REQUIRES_EVAL_RE='([^']+)'", _steps_text(job))
    assert match, "change-type-check has no REQUIRES_EVAL_RE pattern"
    pattern = re.compile(match.group(1))
    enforcement = [POLICY, SETTINGS, MCP_JSON, RUN_AGENT, *SERVERS.values(), *ALLOW_LISTS.values(),
                   os.path.join(AGENTS_DIR, "planner.md"), os.path.join(SKILLS_DIR, "x", "SKILL.md"),
                   os.path.join(ROOT, "scripts", "hooks", "orchestrator-bash-guard.py"),
                   os.path.abspath(__file__)]
    for path in enforcement:
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        assert pattern.match(rel), f"a change to {rel} would not set requires-eval"
    for rel in ("README.md", "src/heretic/p_mobj.c"):
        assert not pattern.match(rel), f"a change to {rel} would needlessly set requires-eval"


def test_advisory_review_cannot_block():
    job = load_workflow()["jobs"][REVIEW_JOB]
    assert job.get("continue-on-error") is True, f"{REVIEW_JOB} must set continue-on-error: true"
    assert REVIEW_JOB not in _gating_jobs(), f"docs/ci-step-design.md classifies {REVIEW_JOB} as gating"
    assert load_ci_design()[REVIEW_JOB].startswith("advisory"), f"{REVIEW_JOB} is not classified advisory"


def test_audit_trail_always_runs_after_every_job():
    jobs = load_workflow()["jobs"]
    job = jobs[AUDIT_JOB]
    assert "always()" in str(job.get("if", "")), f"{AUDIT_JOB} must run with if: always()"
    others = set(jobs) - {AUDIT_JOB}
    assert _needs(job) == others, (
        f"{AUDIT_JOB} needs {sorted(_needs(job))}; it must need every other job: {sorted(others)}")
    # v4 or later: the v3 artifact actions cannot read v4 uploads.
    downloads = [s for s in job.get("steps", [])
                 if re.fullmatch(r"actions/download-artifact@v([4-9]|\d\d+)(\.\S*)?", str(s.get("uses", "")))]
    assert downloads, f"{AUDIT_JOB} does not download artifacts with actions/download-artifact@v4 or later"
    config = downloads[0].get("with", {})
    assert config.get("merge-multiple") is True and "name" not in config, (
        f"{AUDIT_JOB} must download every artifact (no name) with merge-multiple: true")


def test_secret_is_scoped_to_the_reviewer_step():
    """The only secret is the reviewer's purpose-named key, and only the
    reviewer step receives it: not the workflow, not a job, not a
    deterministic step."""
    workflow = load_workflow()
    found = []

    def scan(where, value):
        for name in re.findall(r"secrets\.([A-Za-z0-9_]+)", str(value)):
            found.append((where, name))

    scan("workflow", {k: v for k, v in workflow.items() if k != "jobs"})
    for key, job in workflow["jobs"].items():
        scan(f"job {key}", {k: v for k, v in job.items() if k != "steps"})
        for step in job.get("steps", []):
            scan(f"job {key} step {step.get('name') or step.get('uses')!r}", step)
    allowed = (f"job {REVIEW_JOB} step {REVIEWER_STEP!r}", REVIEWER_SECRET)
    assert found == [allowed], f"secrets referenced outside the reviewer step, or under another name: {found}"
    step = next(s for s in workflow["jobs"][REVIEW_JOB]["steps"] if s.get("name") == REVIEWER_STEP)
    assert REVIEWER_SECRET in step.get("env", {}), "the reviewer secret must arrive through the step's env"


def test_no_key_values_in_ci_files():
    paths = [CI_WORKFLOW, CI_DESIGN]
    scripts = os.path.join(ROOT, "scripts")
    paths += [os.path.join(scripts, n) for n in sorted(os.listdir(scripts)) if n.endswith((".py", ".sh"))]
    leaks = [os.path.relpath(p, ROOT) for p in paths if KEY_SHAPES.search(_read(p))]
    assert not leaks, f"a value shaped like an API key or token is committed in: {leaks}"
