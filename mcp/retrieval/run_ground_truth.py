"""Ground-truth runner for the retrieval server (docs/retrieval-ground-truth.md).

Since Module 4.1 the server decides who may call `retrieve` from AGENT_ROLE
in its own environment (mcp/retrieval/allow-list.json). A server started
without a granted role answers every call with authorization_denied, so the
runner must reach a server started as a granted role.

By default the runner starts its own server over stdio as the planner, the
role these queries stand in for, with the reference corpus and ceiling the
planner's agent file uses:

    python3 mcp/retrieval/run_ground_truth.py

Variables already set in the environment win over these defaults, so a
different corpus or audit log path can be passed the usual way.

To test a server that is already running over HTTP instead, start it with
the same variables and pass its URL:

    AGENT_ROLE=planner \
    RETRIEVAL_REFERENCE_DIR=/workspace/.memory/reference/lessons \
    RETRIEVAL_MAX_CEILING=internal \
    python3 mcp/retrieval/server.py &
    python3 mcp/retrieval/run_ground_truth.py --url http://localhost:8002/mcp
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

THRESHOLD = 0.65
REPO = Path(__file__).resolve().parents[2]
SERVER = Path(__file__).resolve().parent / "server.py"
ROLE = "planner"
STDIO_ENV = {
    "AGENT_ROLE": ROLE,
    "RETRIEVAL_REFERENCE_DIR": str(REPO / ".memory" / "reference" / "lessons"),
    "RETRIEVAL_MAX_CEILING": "internal",
    "RETRIEVAL_AUDIT_LOG": str(REPO / "logs" / "retrieval-audit-log.jsonl"),
}

# One case per ground-truth query in docs/retrieval-ground-truth.md.
# kind selects the pass rule:
# - precision: expected doc in top 3 with score >= THRESHOLD
# - keyword: expected doc returned at all; keyword fallback is allowed
# - ceiling: forbidden doc must be absent
CASES: list[dict[str, Any]] = [
    {
        "id": "Q1",
        "kind": "precision",
        "query": "The container clock already shows tomorrow's date. What date should I put on a new memory entry or run summary?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "expected": "lesson-container-clock-utc.md",
    },
    {
        "id": "Q2",
        "kind": "precision",  # near-miss; decoy lesson-missing-mobj-ierror.md
        "query": "chocolate-heretic exited with code 255 after the DEMO1 timedemo. Does that mean the run failed?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "expected": "lesson-exit-255-normal.md",
    },
    {
        "id": "Q3",
        "kind": "keyword",
        "query": "What does the G_TicHashWrite error mean when a demo run stops early?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "expected": "lesson-missing-mobj-ierror.md",
    },
    {
        "id": "Q4",
        "kind": "precision",  # near-miss; decoy lesson-manifest-format.md
        "query": "Where in the repo should the reference trace for a new Heretic demo be saved?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "expected": "lesson-golden-trace-layout.md",
    },
    {
        "id": "Q5",
        "kind": "ceiling",
        "query": "How does the GIMPL container get its Claude API access, and how should credentials be handled?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "forbidden": "lesson-container-api-credentials.md",
    },
    {
        "id": "Q6",
        "kind": "precision",
        "query": "The demo-suite runner is still a stub, so it can't produce real output. How should I handle this task's acceptance evidence before implementing?",
        "project_id": "proj-lessons",
        "ceiling": "internal",
        "filters": {},
        "expected": "lesson-evidence-gap-substitute-check.md",
    },
]


def extract_hits(result: Any) -> list[dict[str, Any]]:
    """FastMCP versions expose structured tool output under different attributes."""
    if hasattr(result, "data") and result.data is not None:
        return result.data
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return result.structured_content
    if hasattr(result, "structuredContent") and result.structuredContent is not None:
        return result.structuredContent
    if isinstance(result, list):
        return result
    raise RuntimeError(f"Could not extract structured hits from result: {result!r}")


def judge(case: dict[str, Any], hits: list[dict[str, Any]]) -> bool:
    docs = [hit["source_document"] for hit in hits]
    if case["kind"] == "ceiling":
        return case["forbidden"] not in docs
    if case["kind"] == "keyword":
        return case["expected"] in docs
    return any(
        hit["source_document"] == case["expected"]
        and (hit.get("similarity_score") or 0) >= THRESHOLD
        for hit in hits
    )


def summarize(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "(no results)"
    return ", ".join(
        f"{hit['source_document']}#{hit['chunk_index']}"
        f"({hit['retrieval_method']},{hit.get('similarity_score')})"
        for hit in hits
    )


def make_client(url: str | None) -> Client:
    if url:
        return Client(url)
    # The full environment is passed on, so HF_HOME and HF_HUB_OFFLINE from
    # the image still reach the server; AGENT_ROLE is always the planner.
    env = {**STDIO_ENV, **os.environ, "AGENT_ROLE": ROLE}
    return Client(PythonStdioTransport(script_path=SERVER, args=["--stdio"], env=env))


async def main(url: str | None) -> None:
    passed = 0
    async with make_client(url) as client:
        for case in CASES:
            result = await client.call_tool(
                "retrieve",
                {
                    "query": case["query"],
                    "project_id": case["project_id"],
                    "top_k": 3,
                    "classification_ceiling": case["ceiling"],
                    "metadata_filters": case.get("filters", {}),
                },
            )
            hits = extract_hits(result)
            ok = judge(case, hits)
            passed += int(ok)
            print(f"{case['id']}: {'PASS' if ok else 'FAIL'} [{summarize(hits)}]")

    print(f"\n{passed}/{len(CASES)} passed")
    if passed / len(CASES) < 0.80:
        raise SystemExit("Retrieval pass rate is below the 80% floor")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the retrieval ground-truth queries")
    parser.add_argument("--url", help="query a running HTTP server (for example "
                        "http://localhost:8002/mcp) instead of starting one over stdio")
    asyncio.run(main(parser.parse_args().url))
