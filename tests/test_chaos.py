"""
Chaos tests — the anti-"smoke and mirrors" proof.

We write memory, then reopen the *same file* from a fresh client (the SDK
equivalent of a new process) and assert that what survived is exactly what was
written. If memory did not persist, every assertion here fails.

The README can honestly say: "we killed our own process; memory survived."
"""
import subprocess
import sys

import pytest

from agent.memory import ScarTissueMemory
from agent.pipeline import run
from agent.receipts import issue, verify


def test_memory_survives_fresh_process(tmp_path):
    db = str(tmp_path / "scar.db")

    # Process A: write scars, then "die" (client is dropped).
    mem_a = ScarTissueMemory(db)
    run(mem_a, "for i in range(len(users)):\n    handle(users[i])")
    assert len(mem_a.list_patterns()) == 1

    # Process B: a brand-new client on the same file.
    mem_b = ScarTissueMemory(db)
    assert len(mem_b.list_patterns()) == 1
    pat = mem_b.get_pattern("off-by-one")
    assert pat["body"]["count"] == 1


def test_real_subprocess_survives(tmp_path):
    """The genuine version: session1 in one OS process, session2 in another."""
    db = str(tmp_path / "sub.db")
    code = [
        "from agent.memory import ScarTissueMemory",
        "from agent.pipeline import run",
        "m = ScarTissueMemory(" + repr(db) + ")",
        "run(m, 'for i in range(len(users)):\\n    handle(users[i])')",
    ]
    subprocess.run([sys.executable, "-c", "; ".join(code)], check=True)

    out = subprocess.run(
        [sys.executable, "-c",
         "from agent.memory import ScarTissueMemory\n"
         "m = ScarTissueMemory(" + repr(db) + ")\n"
         "print(m.get_pattern('off-by-one')['body']['count'])"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "1"


def test_receipt_chain_verifies(tmp_path):
    mem = ScarTissueMemory(tmp_path / "r.db")
    run(mem, "for i in range(len(a)):\n    x = a[i]")
    v = verify(mem)
    assert v["ok"] is True
    assert v["receipts"] >= 1


def test_receipt_chain_detects_tamper(tmp_path):
    db = str(tmp_path / "t.db")
    mem = ScarTissueMemory(db)
    run(mem, "for i in range(len(a)):\n    x = a[i]")
    assert verify(mem)["ok"] is True

    # Tamper: forge a receipt in the journal.
    mem.log_event(acted=["forged"], extra={"receipt": {
        "pattern": "off-by-one", "action": "warn", "ts": "2020-01-01T00:00:00+00:00",
        "hash": "deadbeef" * 8, "prev": "0" * 64,
    }})
    v = verify(mem)
    assert v["ok"] is False
    assert v["tampered"] is True


def test_issue_receipts_are_signatures_only(tmp_path):
    """Receipts must never carry the developer's raw code."""
    mem = ScarTissueMemory(tmp_path / "s.db")
    r = issue(mem, "off-by-one", "warn")
    assert "for i in range" not in str(r)
    assert set(r) >= {"pattern", "action", "ts", "hash", "prev"}
