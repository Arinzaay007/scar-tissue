# Scar Tissue

**Proof-carrying memory for AI agents.**

> *An agent that remembers what went wrong is an agent you can trust with real power.*

Every company wants to deploy AI agents. Nobody trusts them: they forget
everything, repeat the same mistakes, and can't be audited. Scar Tissue is the
memory layer that fixes the trust — it tracks an agent's recurring failures,
warns *before* it repeats them, and proves what the agent knew.

Built on **[Sibyl Memory](https://sibyllabs.org)** (file-based, five-tier,
SQLite + FTS5, zero embeddings) for the **Sibyl Labs Hackathon · Sep 1–10, 2026**.

---

## The load-bearing statement

> Delete the memory layer and Scar Tissue becomes a generic linter. With it,
> the agent knows your patterns and changes every recommendation.

That asymmetry is the whole product, and it is enforced end to end:

- **A fresh session is a real process boundary.** Session 2 is a brand-new OS
  process that opens the same memory file. The only thing that survives is
  memory.
- **The demo is runnable, not narrated.** `python -m agent.demo all` reproduces
  the whole story in seconds.
- **The receipt chain is tamper-evident.** Every warning is sealed with a
  SHA-256 receipt chained in an append-only journal. Edit any link and
  verification fails.

## Quickstart

```bash
pip install -r requirements.txt

python -m agent.demo all        # the full load-bearing demo
python -m agent.demo decay      # WARM → ARCHIVE → WARM (scar decay & resurface)
python -m agent.demo report     # the scar record + append-only journal

pytest                          # detector, memory, and chaos tests
```

## How it works

The agent loop — `Retrieve → Analyze → Warn → Write → Prove`:

| Step | What happens | Sibyl tier |
|---|---|---|
| Retrieve | load known scars from memory | WARM (`entities/`) |
| Analyze | scan code for anti-patterns | — |
| Warn | known scar → warn *before* the bug lands | WARM read |
| Write | upsert pattern, journal the event | WARM + COLD (`journal/`) |
| Prove | seal with a receipt, advance the chain | COLD + HOT (`state/`) |

### The five tiers (Sibyl's real schema)

| Tier | Directory | Scar Tissue meaning |
|---|---|---|
| HOT | `state/` | live session state + receipt chain head |
| WARM | `entities/` | active scars — single source of truth per pattern |
| COLD | `journal/` | append-only audit trail (detections, warns, tier moves, receipts) |
| REFERENCE | `reference/` | immutable fix library |
| ARCHIVE | `archive/` | cooled scars, recoverable |

### Dynamic storage: scar decay & resurfacing

Memory is not a flat log. A scar you stop repeating **cools off** (WARM →
ARCHIVE). One repeat **reopens it instantly** (ARCHIVE → WARM), with its full
history carried over from the journal. Every move is recorded — the revision
trail judges want to see.

### Signatures only

The receipt hashes the *pattern signature and action* — never your raw code.
Your bug history stays on your machine; only proof leaves. On the Base
integration, the chain head is anchored onchain as signatures.

## Repository layout

```
agent/          the product (memory layer, detectors, pipeline, receipts, demo)
tests/          detector, memory, and chaos tests (real subprocess survival)
index.html      landing page
```

## License

MIT
