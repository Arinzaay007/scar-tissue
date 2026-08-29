"""
Proof-carrying memory — the "Prove" step.

Every warning/birth is sealed with a receipt: a SHA-256 hash over
(previous_receipt, pattern, action, timestamp). Receipts are journaled (COLD,
append-only) and the chain head lives in state (HOT). Recomputing the chain and
comparing to the head detects tampering: edit any link and the chain breaks.

Signatures only. The receipt hashes the *pattern signature and action* — never
the developer's raw code. On Base-integration day, this chain head is what gets
anchored onchain: a judge sees a tx hash proving what the agent knew, while the
private code never leaves the machine. "Export denied — signatures only."
"""
from __future__ import annotations

import hashlib

from .memory import now_iso

CHAIN_HEAD_KEY = "receipt_head"
RECEIPT_COUNT_KEY = "receipt_count"
GENESIS = "0" * 64


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def issue(memory, pattern: str, action: str) -> dict:
    """Seal one memory write with a receipt; advance the chain head.

    Each receipt carries a monotonic `seq` so the chain can be replayed in the
    exact order it was written, independent of journal read order.
    """
    session = memory.get_session() or {}
    prev = session.get(CHAIN_HEAD_KEY, GENESIS)
    seq = int(session.get(RECEIPT_COUNT_KEY, 0)) + 1
    ts = now_iso()
    h = _sha256(f"{prev}|{pattern}|{action}|{ts}")
    receipt = {
        "seq": seq, "pattern": pattern, "action": action,
        "ts": ts, "hash": h, "prev": prev,
    }
    memory.log_event(acted=[f"receipt  {pattern}  {action}"], extra={"receipt": receipt})
    session[CHAIN_HEAD_KEY] = h
    session[RECEIPT_COUNT_KEY] = seq
    memory.set_session(session)
    return receipt


def verify(memory) -> dict:
    """Recompute the whole chain from the journal and compare to the stored head."""
    session = memory.get_session() or {}
    head = session.get(CHAIN_HEAD_KEY, GENESIS)

    receipts = []
    for ev in memory.read_journal(limit=2000):
        receipt = (ev.get("extra") or {}).get("receipt")
        if receipt:
            receipts.append(receipt)
    receipts.sort(key=lambda r: int(r.get("seq", 0)))

    prev = GENESIS
    for n, r in enumerate(receipts):
        expected = _sha256(f"{prev}|{r['pattern']}|{r['action']}|{r['ts']}")
        if expected != r["hash"]:
            return {"ok": False, "tampered": True, "at_receipt": n, "head": head}
        prev = r["hash"]

    return {
        "ok": prev == head,
        "tampered": prev != head,
        "receipts": len(receipts),
        "head": head[:12] + "...",
    }
