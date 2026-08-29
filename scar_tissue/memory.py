from sibyl_memory_client import Storage, MemoryClient
from datetime import datetime
import os

class ScarTissueMemory:
    def __init__(self, tenant_id="default", db_path=None):
        if db_path is None:
            db_path = os.path.expanduser("~/.scar-tissue/memory.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.storage = Storage(db_path=db_path)
        self.client = MemoryClient(storage=self.storage, tenant_id=tenant_id)
        self.tenant_id = tenant_id

    def update_active_pattern(self, name, count, last_seen):
        self.client.set_state(key=f"anti_pattern/{name}", body={"pattern": name, "count": count, "last_seen": last_seen})

    def get_pattern_entity(self, name):
        try: return self.client.get_entity(category="anti_pattern", name=name)
        except: return None

    def upsert_pattern_entity(self, name, data):
        self.client.set_entity(category="anti_pattern", name=name, body=data)

    def log_bug(self, bug_type, file_path, line, root_cause, fix="", context=""):
        self.client.write_event(evaluated={"type": bug_type, "file": file_path, "line": line, "root_cause": root_cause, "fix": fix})

    def recall(self, query, limit=8):
        results = self.client.search(query=query, limit=limit)
        tiers = {"state": [], "entity": [], "journal": [], "reference": []}
        for r in results:
            t = r.get("tier", "unknown")
            if t in tiers: tiers[t].append(r)
        return tiers

    def format_context(self, tiers):
        lines = []
        if tiers["state"]:
            lines.append("## Active Anti-Patterns")
            for p in tiers["state"]:
                b = p.get("body", {})
                if isinstance(b, dict):
                    lines.append(f"- {b.get('pattern','?')}: {b.get('count',0)} occurrences")
        if tiers["entity"]:
            lines.append("\n## Known Patterns")
            for p in tiers["entity"]:
                b = p.get("body", {})
                if isinstance(b, dict):
                    lines.append(f"- {p.get('key','?')}: {b.get('count',0)} times")
        if tiers["journal"]:
            lines.append("\n## Recent Bug History")
            for b in tiers["journal"][:5]:
                body = b.get("body", {})
                if isinstance(body, dict):
                    ev = body.get("evaluated", body)
                    lines.append(f"- {ev.get('type','?')} in {ev.get('file','?')}:{ev.get('line','?')}")
        return "\n".join(lines) if lines else "(no memories yet)"
