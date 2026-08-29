"""
Scar Tissue memory layer — built on Sibyl Memory (the real engine, no fakes).

Maps Scar Tissue's five tiers onto Sibyl Memory's actual five-tier schema:

    HOT        -> state/      live working state of the session
    WARM       -> entities/   active scars (single source of truth per pattern)
    COLD       -> journal/    append-only audit trail (detections, warns, tier moves)
    REFERENCE  -> reference/  immutable fix library (rules that never change)
    ARCHIVE    -> archive/    cooled scars (no repeats), recoverable on resurface

The dynamic-storage story ("scar decay & resurfacing") is implemented as real
moves between tiers:

    new repeat  -> WARM  (set_entity)
    no repeats  -> WARM -> ARCHIVE  (archive_entity)   # the scar cools off
    one repeat  -> ARCHIVE -> WARM  (set_entity)       # the scar reopens

Every move is journaled, so the full revision trail is recoverable from COLD
even after an entity has been archived out of the active set.

Sibyl enforces Rule 43 at the schema level: UNIQUE (tenant_id, category, name).
Two rows describing the same pattern cannot coexist — drift is impossible.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sibyl_memory_client import MemoryClient

CATEGORY = "anti-pattern"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ScarTissueMemory:
    """A thin, honest wrapper over the Sibyl MemoryClient.

    Nothing here hides the engine — it encodes *how* Scar Tissue uses the five
    tiers so the demo and the tests both exercise the real SDK underneath.
    """

    def __init__(self, path: str | Path = "~/.sibyl-memory/scar-tissue.db"):
        self.path = str(Path(path).expanduser())
        self._client = MemoryClient.local(self.path)

    # ------------------------------------------------------------------ HOT
    def set_session(self, body: dict) -> None:
        self._client.set_state("session", body)

    def get_session(self) -> dict | None:
        raw = self._client.get_state("session")
        # get_state returns {"body": ..., "updated_at": ...}; unwrap the body.
        return raw["body"] if raw else None

    # ----------------------------------------------------------------- WARM
    def upsert_pattern(
        self,
        signature: str,
        *,
        lang: str,
        suggestion: str,
        evidence: str | None = None,
        severity: str = "medium",
    ) -> dict:
        """Create or re-open a scar. Returns {'new': bool, 'body': {...}}."""
        existing = self.get_pattern(signature)
        if existing is None:
            body = {
                "lang": lang,
                "suggestion": suggestion,
                "severity": severity,
                "count": 1,
                "first_seen": now_iso(),
                "last_seen": now_iso(),
                "evidence": evidence,
            }
            self._client.set_entity(CATEGORY, signature, body)
            self.log_event(acted=[f"scar.born  {signature}  lang={lang}"])
            return {"new": True, "pattern": signature, "body": body}

        body = dict(existing["body"])
        body["count"] = int(body.get("count", 0)) + 1
        body["last_seen"] = now_iso()
        if evidence:
            body["evidence"] = evidence
        self._client.set_entity(CATEGORY, signature, body)
        self.log_event(
            acted=[f"scar.reopened  {signature}  count={body['count']}"]
        )
        return {"new": False, "pattern": signature, "body": body}

    def get_pattern(self, signature: str) -> dict | None:
        try:
            return self._client.get_entity(CATEGORY, signature)
        except Exception:
            return None

    def list_patterns(self) -> list[dict]:
        return self._client.list_entities(CATEGORY)

    def recall(self, query: str) -> list[dict]:
        """FTS5 search across everything the agent remembers."""
        return self._client.search_entities(query)

    # ----------------------------------------------------------------- COLD
    def log_event(self, *, acted=None, evaluated=None, forward=None, extra=None) -> str:
        return self._client.write_event(
            acted=acted, evaluated=evaluated, forward=forward, extra=extra
        )

    def read_journal(self, *, limit: int = 500) -> list[dict]:
        return self._client.read_events(limit=limit)

    # ----------------------------------------------- ARCHIVE (dynamic storage)
    def cool_down(self, signature: str, *, reason: str) -> dict:
        """WARM -> ARCHIVE: a scar that has not repeated cools off."""
        if self.get_pattern(signature) is None:
            raise KeyError(f"unknown pattern {signature!r}")
        result = self._client.archive_entity(CATEGORY, signature, reason=reason)
        self.log_event(
            acted=[f"tier.move  {signature}  WARM->ARCHIVE  reason={reason}"]
        )
        return result

    def resurface(
        self,
        signature: str,
        *,
        lang: str,
        suggestion: str,
        evidence: str | None = None,
        severity: str = "medium",
        prior_count: int = 0,
    ) -> dict:
        """ARCHIVE -> WARM: a cooled scar reopens the moment it repeats.

        The prior count survives in the journal, so the reopened scar resumes
        its history instead of starting from zero.
        """
        body = {
            "lang": lang,
            "suggestion": suggestion,
            "severity": severity,
            "count": prior_count + 1,
            "first_seen": now_iso(),
            "last_seen": now_iso(),
            "evidence": evidence,
            "resurfaced": True,
        }
        self._client.set_entity(CATEGORY, signature, body)
        self.log_event(
            acted=[f"tier.move  {signature}  ARCHIVE->WARM  reopened"]
        )
        return body

    # ------------------------------------------------------------- REFERENCE
    def seed_references(self, rules: dict[str, str]) -> None:
        """Immutable fix library: signature -> plain-text guidance."""
        for signature, text in rules.items():
            self._client.set_reference(f"fix:{signature}", text)
