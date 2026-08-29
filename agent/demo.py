"""
Scar Tissue — terminal demo.

The load-bearing proof, in one command:

    python -m agent.demo all

It runs two *separate processes* against the *same* memory file:

    session1   process A writes a scar to memory, then dies.
    session2   a brand-new process B opens the same file, recalls the scar,
               and warns BEFORE the bug repeats.

The "fresh session" is a real process boundary, not a narration. Memory is the
only thing that survives. Delete it and session 2 becomes a stateless linter.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .memory import ScarTissueMemory
from .pipeline import run
from .receipts import verify

# ── ANSI ────────────────────────────────────────────────────────────────────
C = {
    "dim": "\033[2m", "bold": "\033[1m",
    "rust": "\033[38;5;167m", "gold": "\033[38;5;178m",
    "green": "\033[38;5;108m", "red": "\033[38;5;203m",
    "grey": "\033[38;5;245m", "reset": "\033[0m",
}


def _c(color: str, text: str) -> str:
    return f"{C[color]}{text}{C['reset']}"


def _banner() -> None:
    print(_c("rust", "\n  ═══════════════════════════════════════════════════════════"))
    print(_c("bold", "   SCAR TISSUE ") + _c("dim", "— proof-carrying memory for agents"))
    print(_c("dim", "   engine: ") + "Sibyl Memory (SQLite + FTS5 · file-based)")
    print(_c("rust", "  ═══════════════════════════════════════════════════════════\n"))


SESSION1_CODE = """\
def process_users(users):
    for i in range(len(users)):
        handle(users[i])

def load_config(path):
    try:
        return open(path).read()
    except FileNotFoundError:
        pass

def add_to_group(name, members=[]):
    members.append(name)
    return members
"""

SESSION2_CODE = """\
def find_admin(users):
    for i in range(len(users)):
        if users[i].role == "admin":
            return users[i]

def get_plan(cfg):
    return cfg.get("plan").billing
"""


def _print_findings(title: str, items: list[dict], color: str) -> None:
    if not items:
        print(_c("grey", f"   (none)"))
        return
    for it in items:
        print(f"   {_c(color, '■')} {_c('bold', it['title'])}")
        print(f"     {_c('dim', 'evidence  ')} {it['evidence']}")
        print(f"     {_c('dim', 'fix       ')} {it['suggestion']}")
        if "count" in it:
            print(f"     {_c('rust', f'repeats   ')} {it['count']}×")


def session1(db: str) -> None:
    _banner()
    print(_c("gold", " SESSION 1 — process A\n") + _c("dim", "  watching code being written…\n"))
    mem = ScarTissueMemory(db)

    print(_c("dim", "  >>> analyze"))
    result = run(mem, SESSION1_CODE)
    print(f"\n   {_c('gold','★')} NEW SCARS BORN (written to memory):")
    _print_findings("births", result["births"], "gold")

    print(f"\n {_c('dim','memory file:')} {mem.path}")
    print(f" {_c('dim','scars in WARM:')} {len(mem.list_patterns())}")
    print(_c("red", "\n  ✗ process A ends here — its memory is on disk, not in RAM\n"))


def session2(db: str) -> None:
    _banner()
    print(_c("green", " SESSION 2 — a brand-new process B\n") + _c("dim", "  fresh process, same memory file\n"))
    mem = ScarTissueMemory(db)

    # RETRIEVE
    known = mem.list_patterns()
    print(_c("dim", "  >>> retrieve  (what did process B inherit?)\n"))
    if known:
        for p in known:
            b = p["body"]
            print(
                f"   {_c('gold','▣')} {_c('bold', p['name'])}  "
                f"{_c('dim', f"count={b['count']} · {b['suggestion'][:44]}")}"
            )
    else:
        print(_c("grey", "   (nothing — empty memory)"))

    print(_c("dim", "\n  >>> analyze"))
    result = run(mem, SESSION2_CODE)

    print(f"\n   {_c('red','⚠')} WARNED BEFORE REPEAT (recalled from memory):")
    _print_findings("warns", result["warns"], "red")
    print(f"\n   {_c('gold','★')} NEW SCAR BORN:")
    _print_findings("births", result["births"], "gold")

    print(f"\n {_c('dim','memory file:')} {mem.path}")
    print(f" {_c('dim','scars in WARM:')} {len(mem.list_patterns())}\n")


def verify_cmd(db: str) -> None:
    _banner()
    mem = ScarTissueMemory(db)
    v = verify(mem)
    print(_c("dim", "  >>> verify receipt chain\n"))
    if v["ok"]:
        print(f"   {_c('green','✔')} chain intact — {v['receipts']} receipts, head {v['head']}")
    else:
        print(f"   {_c('red','✗')} TAMPERED — receipt {v.get('at_receipt')} does not verify")
    print()


def report_cmd(db: str) -> None:
    _banner()
    mem = ScarTissueMemory(db)
    print(_c("dim", "  >>> scar record\n"))
    for p in mem.list_patterns():
        b = p["body"]
        print(f"   {_c('bold', p['name'])}")
        print(f"     {_c('dim','count     ')} {b['count']}")
        print(f"     {_c('dim','first_seen')} {b['first_seen']}")
        print(f"     {_c('dim','last_seen ')} {b['last_seen']}")
        print(f"     {_c('dim','suggestion')} {b['suggestion']}")
        print()
    print(_c("dim", "  >>> journal (append-only audit trail)\n"))
    for ev in mem.read_journal(limit=50):
        acted = " · ".join(ev.get("acted") or [])
        print(f"   {_c('grey', ev['ts'][11:19])}  {acted}")
    print()


def decay_cmd(db: str) -> None:
    """Demo the dynamic-storage story: WARM -> ARCHIVE -> WARM."""
    _banner()
    mem = ScarTissueMemory(db)
    sig = "off-by-one"
    pat = mem.get_pattern(sig)
    if pat is None:
        print(_c("red", f"   no scar '{sig}' in memory — run session1 first\n"))
        return

    print(_c("dim", f"  >>> {sig} has not repeated for 30 days\n"))
    print(_c("rust", f"   tier.move  {sig}  WARM → ARCHIVE  (cooled off)"))
    mem.cool_down(sig, reason="no repeats in 30 days")
    print(f"   {_c('dim','active scars:')} {len(mem.list_patterns())}  (the scar is no longer in the active set)\n")

    print(_c("dim", "  >>> one repeat reopens it instantly\n"))
    print(_c("rust", f"   tier.move  {sig}  ARCHIVE → WARM  (reopened)"))
    mem.resurface(
        sig,
        lang="python",
        suggestion="Use `enumerate()` to iterate without manual indexing.",
        evidence="for i in range(len(users))",
        severity="high",
        prior_count=pat["body"].get("count", 0),
    )
    reopened = mem.get_pattern(sig)
    print(f"   {_c('bold','reopened count:')} {reopened['body']['count']}  (history carried over)\n")


def all_cmd(db: str) -> None:
    session1(db)
    sys.stdout.flush()  # child writes straight to the pipe; don't let our buffer race it
    print(_c("dim", "  ── process A is gone. spawning process B ───────────────────────────\n"))
    # A genuinely fresh process opens the same memory file.
    subprocess.run([sys.executable, "-m", "agent.demo", "session2", "--db", db], check=True)
    verify_cmd(db)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scar-tissue", description=__doc__)
    p.add_argument("cmd", choices=["session1", "session2", "all", "verify", "report", "decay"], nargs="?", default="all")
    p.add_argument("--db", default=os.environ.get("SCAR_TISSUE_DB", "~/.sibyl-memory/scar-tissue.db"))
    args = p.parse_args(argv)

    # Keep stdout line-buffered even when piped, so the session order reads true.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    db = str(Path(args.db).expanduser())
    {"session1": session1, "session2": session2, "all": all_cmd,
     "verify": verify_cmd, "report": report_cmd, "decay": decay_cmd}[args.cmd](db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
