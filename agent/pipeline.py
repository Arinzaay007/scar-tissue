"""
The agent loop: Retrieve -> Analyze -> Warn -> Write -> Prove.

    1. RETRIEVE  load the known scars from memory (WARM)
    2. ANALYZE   scan the code for anti-patterns
    3. WARN      if a finding matches a known scar, warn BEFORE the bug lands
    4. WRITE     upsert the pattern and journal the event (memory is load-bearing)
    5. PROVE     seal the action with a receipt (tamper-evident chain)

Delete the memory layer and this loop degrades to a stateless linter:
it can still *find* the pattern, but it can no longer *warn* from history
or *prove* what it knew. That asymmetry is the whole product.
"""
from __future__ import annotations

from . import detector, receipts


def run(memory, code: str, *, lang: str = "python", issue_receipts: bool = True) -> dict:
    # 1. RETRIEVE — what does the agent already remember?
    known_before = {p["name"] for p in memory.list_patterns()}

    # 2. ANALYZE
    findings = detector.scan(code)

    # 3+4. WARN + WRITE
    warns: list[dict] = []
    births: list[dict] = []
    for f in findings:
        was_known = f["signature"] in known_before
        result = memory.upsert_pattern(
            f["signature"],
            lang=lang,
            suggestion=f["suggestion"],
            evidence=f["evidence"],
            severity=f["severity"],
        )
        entry = {
            "signature": f["signature"],
            "title": f["title"],
            "evidence": f["evidence"],
            "suggestion": f["suggestion"],
            "severity": f["severity"],
            "count": result["body"]["count"],
        }
        (warns if was_known else births).append(entry)

        # 5. PROVE
        if issue_receipts:
            receipts.issue(memory, f["signature"], "warn" if was_known else "birth")

    return {"findings": findings, "warns": warns, "births": births}
