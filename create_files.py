import os

os.makedirs("scar_tissue", exist_ok=True)

# __init__.py
with open("scar_tissue/__init__.py", "w") as f:
    f.write("# Scar Tissue\n")

# alert.py
with open("scar_tissue/alert.py", "w") as f:
    f.write("import sys\n\ndef play_tone(frequency=440, duration=0.5):\n    try:\n        if sys.platform == 'win32':\n            import winsound\n            winsound.Beep(frequency, int(duration * 1000))\n        else:\n            print('\\\\a', end='', flush=True)\n    except: pass\n\ndef play_faaaaa():\n    play_tone(280, 1.2)\n\ndef play_compound_alert(count):\n    if count >= 2:\n        play_faaaaa()\n    else:\n        play_tone(440, 0.3)\n")

# memory.py
with open("scar_tissue/memory.py", "w") as f:
    f.write("""from sibyl_memory_client import Storage, MemoryClient
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
            lines.append("\\n## Known Patterns")
            for p in tiers["entity"]:
                b = p.get("body", {})
                if isinstance(b, dict):
                    lines.append(f"- {p.get('key','?')}: {b.get('count',0)} times")
        if tiers["journal"]:
            lines.append("\\n## Recent Bug History")
            for b in tiers["journal"][:5]:
                body = b.get("body", {})
                if isinstance(body, dict):
                    ev = body.get("evaluated", body)
                    lines.append(f"- {ev.get('type','?')} in {ev.get('file','?')}:{ev.get('line','?')}")
        return "\\n".join(lines) if lines else "(no memories yet)"
""")

# detector.py
with open("scar_tissue/detector.py", "w") as f:
    f.write("""import re
from dataclasses import dataclass

@dataclass
class AntiPattern:
    name: str
    severity: str
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    suggested_fix: str
    code_fix: str
    confidence: float

class AntiPatternDetector:
    PATTERNS = {
        "off_by_one": {"name": "Off-by-one error", "severity": "high", "regex": [r"range\\\\(len\\\\((\\\\w+)\\\\)\\\\)"], "description": "Manual indexing with range(len(x)) is error-prone.", "fix": "Use enumerate()."},
        "manual_indexing": {"name": "Manual indexing", "severity": "medium", "regex": [r"(\\\\w+)\\\\[i\\\\]"], "description": "Use enumerate() for index + value.", "fix": "Use enumerate()."},
        "bare_except": {"name": "Bare except clause", "severity": "high", "regex": [r"except\\\\s*:"], "description": "Bare except catches everything.", "fix": "Catch specific exceptions."},
        "mutable_default": {"name": "Mutable default argument", "severity": "high", "regex": [r"def \\\\w+\\\\([^)]*=\\\\s*\\\\[", r"def \\\\w+\\\\([^)]*=\\\\s*\\\\{"], "description": "Mutable defaults are shared across calls.", "fix": "Use None as default."},
        "hardcoded_secret": {"name": "Hardcoded secret", "severity": "critical", "regex": [r"password\\\\s*=", r"secret\\\\s*=", r"api_key\\\\s*="], "description": "Hardcoded secrets are a security risk.", "fix": "Use environment variables."},
        "eval_usage": {"name": "eval() usage", "severity": "critical", "regex": [r"\\\\beval\\\\("], "description": "eval() executes arbitrary code.", "fix": "Use ast.literal_eval()."},
        "global_variable": {"name": "Global variable mutation", "severity": "medium", "regex": [r"global\\\\s+\\\\w+"], "description": "Global variables make code hard to test.", "fix": "Use a class."},
        "print_debug": {"name": "print() for debugging", "severity": "low", "regex": [r"^\\\\s*print\\\\("], "description": "Use logging instead of print().", "fix": "Replace with logging."},
    }

    def __init__(self):
        self.compiled = {}
        for k, p in self.PATTERNS.items():
            if p["regex"]:
                self.compiled[k] = {**p, "re": [re.compile(r) for r in p["regex"]]}

    def detect(self, code, file_path="<stdin>"):
        findings = []
        for i, line in enumerate(code.split("\\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            for k, p in self.compiled.items():
                for regex in p["re"]:
                    if regex.search(line):
                        conf = 0.8 if p["severity"] in ("critical", "high") else 0.6
                        findings.append(AntiPattern(p["name"], p["severity"], file_path, i, stripped, p["description"], p["fix"], "", conf))
                        break
        return findings
""")

# agent.py
with open("scar_tissue/agent.py", "w") as f:
    f.write("""import json
from datetime import datetime
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .memory import ScarTissueMemory
from .detector import AntiPatternDetector
from .alert import play_compound_alert

class AgentState(TypedDict):
    messages: list
    user_id: str
    project: str
    code_input: str
    recalled_context: str
    findings: list
    warning: str
    receipt: dict

def retrieve_memories(state, memory):
    query = state.get("code_input", "")[:200]
    tiers = memory.recall(query, limit=8)
    return {"recalled_context": memory.format_context(tiers)}

def analyze_code(state, detector):
    code = state.get("code_input", "")
    return {"findings": detector.detect(code) if code else []}

def generate_warning(state, memory):
    findings = state.get("findings", [])
    context = state.get("recalled_context", "")
    if not findings:
        return {"warning": ""}
    parts = []
    for f in findings:
        entity = memory.get_pattern_entity(f.name.lower().replace(" ", "_"))
        if entity:
            body = entity.get("body", {})
            count = body.get("count", 1) if isinstance(body, dict) else 1
            parts.append(f"[!] {f.name} (line {f.line_number})\\n   You have hit this pattern {count} times before.\\n   {f.description}\\n   Fix: {f.suggested_fix}")
            play_compound_alert(count)
        else:
            parts.append(f"[!] {f.name} (line {f.line_number})\\n   {f.description}\\n   Fix: {f.suggested_fix}")
            play_compound_alert(1)
    if context and context != "(no memories yet)":
        parts.append(f"\\n[i] From your memory:\\n{context}")
    return {"warning": "\\n\\n".join(parts)}

def write_memories(state, memory):
    for f in state.get("findings", []):
        memory.log_bug(f.name, f.file_path, f.line_number, f.description, f.suggested_fix, f.code_snippet)
        key = f.name.lower().replace(" ", "_")
        existing = memory.get_pattern_entity(key)
        body = existing.get("body", {}) if existing else {}
        if isinstance(body, dict):
            body["count"] = body.get("count", 0) + 1
            body["last_seen"] = f.file_path
        else:
            body = {"count": 1, "last_seen": f.file_path, "severity": f.severity}
        memory.upsert_pattern_entity(key, body)
        memory.update_active_pattern(key, body.get("count", 1), f.file_path)
    return {}

def generate_receipt(state):
    findings = state.get("findings", [])
    if not findings:
        return {"receipt": {}}
    context = state.get("recalled_context", "")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    receipt = {
        "receipt_id": f"str-{ts}",
        "timestamp": datetime.utcnow().isoformat(),
        "findings_count": len(findings),
        "patterns": [f.name for f in findings],
        "memory_tiers_used": [],
        "status": "generated"
    }
    for tier, marker in [("HOT","Active"),("WARM","Known"),("COLD","Bug"),("REFERENCE","Convention")]:
        if marker in context:
            receipt["memory_tiers_used"].append(tier)
    return {"receipt": receipt}

def build_agent(memory, detector):
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", lambda s: retrieve_memories(s, memory))
    graph.add_node("analyze", lambda s: analyze_code(s, detector))
    graph.add_node("warn", lambda s: generate_warning(s, memory))
    graph.add_node("write", lambda s: write_memories(s, memory))
    graph.add_node("prove", generate_receipt)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "warn")
    graph.add_edge("warn", "write")
    graph.add_edge("write", "prove")
    graph.add_edge("prove", END)
    return graph.compile()

def run_agent(code, user_id="default", project="default"):
    memory = ScarTissueMemory(tenant_id=user_id)
    detector = AntiPatternDetector()
    agent = build_agent(memory, detector)
    result = agent.invoke({
        "messages": [HumanMessage(content=code)],
        "user_id": user_id,
        "project": project,
        "code_input": code,
        "recalled_context": "",
        "findings": [],
        "warning": "",
        "receipt": {}
    })
    return {
        "warning": result.get("warning", ""),
        "receipt": result.get("receipt", {}),
        "findings": result.get("findings", []),
        "context": result.get("recalled_context", "")
    }
""")

# __main__.py
with open("scar_tissue/__main__.py", "w") as f:
    f.write("""import sys, json
from .agent import run_agent

EXAMPLE_CODE = \"\"\"
def get_user(user_id):
    users = fetch_all_users()
    for i in range(len(users)):
        if users[i].id == user_id:
            return users[i]

def process_data(data=[]):
    data.append(1)
    return data

password = "super_secret_password_123"
\"\"\"

def main():
    if len(sys.argv) < 2:
        print("Scar Tissue - The Agent That Remembers What Broke You")
        print()
        print("Usage: python -m scar_tissue demo")
        return
    cmd = sys.argv[1]
    if cmd == "demo":
        print("Scar Tissue - Demo")
        print()
        result = run_agent(EXAMPLE_CODE, user_id="demo-user")
        if result["warning"]:
            print(result["warning"])
            receipt = json.dumps(result["receipt"], indent=2)
            print(f"\\nReceipt: {receipt}")
        else:
            print("No anti-patterns detected.")

if __name__ == "__main__":
    main()
""")

print("All files created!")
