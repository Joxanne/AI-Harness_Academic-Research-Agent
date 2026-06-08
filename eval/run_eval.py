"""
Evaluation script for the Academic Research Agent.

Metrics:
  1. governance_accuracy  — blocked cases correctly intercepted
  2. router_accuracy      — intent correctly classified
  3. task_success_rate    — all expected_tools appear in execution trace
  4. budget_compliance    — turns_used <= max_turns (12)

Usage:
  cd "c:\\資工人生\\碩士\\AIoT\\HW4_Survey of DRL"
  python eval/run_eval.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import time
from pathlib import Path

from src.agent import ResearchAgent

TESTSET_PATH = Path(__file__).parent / "testset.json"
RESULTS_PATH = Path(__file__).parent / "results.json"
MAX_TURNS = 12


async def run_case(agent: ResearchAgent, case: dict) -> dict:
    """Run a single test case and return evaluation result."""
    tools_called: list[str] = []
    intent_seen: str | None = None
    was_blocked = False
    turns_used = 0

    async def on_step(tool_name: str, args: dict, result):
        nonlocal intent_seen, was_blocked, turns_used
        tools_called.append(tool_name)
        if tool_name == "_governance" and isinstance(result, dict):
            if result.get("blocked"):
                was_blocked = True
        if tool_name == "_router" and isinstance(result, dict):
            intent_seen = result.get("intent")
        if tool_name == "_groundedness" and isinstance(result, dict):
            turns_used = result.get("turns_used", turns_used)

    try:
        t0 = time.time()
        answer = await agent.run(case["query"], on_step=on_step)
        latency = round(time.time() - t0, 2)
    except Exception as e:
        return {
            "id": case["id"],
            "scenario": case["scenario"],
            "error": str(e),
            "governance_ok": False,
            "router_ok": False,
            "task_ok": False,
            "budget_ok": True,
            "latency": 0,
        }

    # ── Evaluate metrics ─────────────────────────────────────────────────
    # 1. Governance
    if case["should_be_blocked"]:
        governance_ok = was_blocked
    else:
        governance_ok = not was_blocked

    # 2. Router
    if case["expected_intent"] is None:
        router_ok = True  # blocked cases don't need routing
    else:
        router_ok = intent_seen == case["expected_intent"]

    # 3. Task success — all expected tools must appear in trace
    expected = case.get("expected_tools", [])
    if expected:
        task_ok = all(t in tools_called for t in expected)
    else:
        task_ok = True  # no tools expected (e.g., blocked / out_of_scope)

    # 4. Budget compliance
    budget_ok = turns_used <= MAX_TURNS

    return {
        "id": case["id"],
        "scenario": case["scenario"],
        "query": case["query"][:80],
        "governance_ok": governance_ok,
        "router_ok": router_ok,
        "task_ok": task_ok,
        "budget_ok": budget_ok,
        "intent_seen": intent_seen,
        "tools_called": [t for t in tools_called if not t.startswith("_")],
        "was_blocked": was_blocked,
        "turns_used": turns_used,
        "latency": latency,
    }


async def main():
    cases = json.loads(TESTSET_PATH.read_text(encoding="utf-8"))
    results = []
    agent = ResearchAgent()

    print(f"\n{'='*60}")
    print(f"  Academic Research Agent — Evaluation ({len(cases)} cases)")
    print(f"{'='*60}\n")

    for i, case in enumerate(cases, 1):
        print(f"[{i:02d}/{len(cases)}] {case['id']} ({case['scenario']}) — {case['query'][:50]}...")
        result = await run_case(agent, case)
        results.append(result)
        agent.reset()  # fresh chat per case

        gov = "✓" if result["governance_ok"] else "✗"
        rou = "✓" if result["router_ok"]    else "✗"
        tsk = "✓" if result["task_ok"]      else "✗"
        bud = "✓" if result["budget_ok"]    else "✗"
        print(f"       gov={gov}  router={rou}  task={tsk}  budget={bud}  "
              f"intent={result.get('intent_seen')}  latency={result.get('latency')}s")

        # Small delay to avoid rate limits
        if i < len(cases):
            await asyncio.sleep(2)

    # ── Aggregate metrics ────────────────────────────────────────────────
    n = len(results)
    governance_accuracy = sum(r["governance_ok"] for r in results) / n
    router_accuracy     = sum(r["router_ok"]     for r in results) / n
    task_success_rate   = sum(r["task_ok"]        for r in results) / n
    budget_compliance   = sum(r["budget_ok"]      for r in results) / n
    avg_latency         = sum(r.get("latency", 0) for r in results) / n

    summary = {
        "total_cases": n,
        "governance_accuracy": round(governance_accuracy * 100, 1),
        "router_accuracy":     round(router_accuracy     * 100, 1),
        "task_success_rate":   round(task_success_rate   * 100, 1),
        "budget_compliance":   round(budget_compliance   * 100, 1),
        "avg_latency_s":       round(avg_latency, 2),
        "cases": results,
    }

    RESULTS_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  Governance Accuracy  : {summary['governance_accuracy']}%")
    print(f"  Router Accuracy      : {summary['router_accuracy']}%")
    print(f"  Task Success Rate    : {summary['task_success_rate']}%")
    print(f"  Budget Compliance    : {summary['budget_compliance']}%")
    print(f"  Avg Latency          : {summary['avg_latency_s']}s")
    print(f"\n  Results saved → {RESULTS_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
