import json
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
            parts.append(f"[!] {f.name} (line {f.line_number})\n   You have hit this pattern {count} times before.\n   {f.description}\n   Fix: {f.suggested_fix}")
            play_compound_alert(count)
        else:
            parts.append(f"[!] {f.name} (line {f.line_number})\n   {f.description}\n   Fix: {f.suggested_fix}")
            play_compound_alert(1)
    if context and context != "(no memories yet)":
        parts.append(f"\n[i] From your memory:\n{context}")
    return {"warning": "\n\n".join(parts)}

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
