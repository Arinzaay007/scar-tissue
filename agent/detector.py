"""
Anti-pattern detectors.

Each detector is a pure function: source code -> list of findings. A finding has
a stable `signature` (the entity name stored in memory — the "scar"), the
evidence that triggered it, and a concrete suggestion.

The signatures map to the scar types on the landing page:
    off-by-one      "Off-by-one errors"
    unchecked-get   "Null / unhandled None"
    bare-except     "Missing error handling"
    except-pass     "Missing error handling" (silent variant)
    mutable-default "Over-engineering / footguns"
"""
from __future__ import annotations

import ast
import re


def _finding(signature, title, evidence, suggestion, severity="medium", location=None):
    return {
        "signature": signature,
        "title": title,
        "evidence": evidence,
        "suggestion": suggestion,
        "severity": severity,
        "location": location,
    }


def detect_off_by_one(code: str) -> list[dict]:
    # for i in range(len(seq)):  ->  manual indexing, off-by-one risk
    out = []
    pat = re.compile(r"for\s+(\w+)\s+in\s+range\s*\(\s*len\s*\((\w+)\)")
    for m in pat.finditer(code):
        i, seq = m.group(1), m.group(2)
        out.append(_finding(
            "off-by-one",
            "Off-by-one manual indexing",
            f"for {i} in range(len({seq}))",
            f"Use `for {i}, item in enumerate({seq}):` and iterate items directly.",
            severity="high",
        ))
    return out


def detect_bare_except(code: str) -> list[dict]:
    # `except:` with no type swallows everything, including KeyboardInterrupt
    out = []
    for m in re.finditer(r"except\s*:", code):
        out.append(_finding(
            "bare-except",
            "Bare except clause",
            "except:",
            "Catch specific exception types so unrelated failures are not swallowed.",
            severity="medium",
        ))
    return out


def detect_except_pass(code: str) -> list[dict]:
    # `except X: pass` silently drops the error
    out = []
    pat = re.compile(r"except[^:]*:\s*pass\b")
    for m in pat.finditer(code):
        out.append(_finding(
            "except-pass",
            "Swallowed exception",
            m.group(0).strip(),
            "Log the error or re-raise instead of silently passing.",
            severity="medium",
        ))
    return out


def detect_mutable_default(code: str) -> list[dict]:
    # def f(x=[]): / def f(x={}):  ->  one shared object across all calls
    out = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.args.defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    out.append(_finding(
                        "mutable-default",
                        "Mutable default argument",
                        f"def {node.name}(...={ast.unparse(d)})",
                        "Default to `None` and create the container inside the function body.",
                        severity="medium",
                        location=node.name,
                    ))
    return out


def detect_unchecked_get(code: str) -> list[dict]:
    # d.get('k').attr  ->  .get() can return None, then the attribute access crashes
    out = []
    pat = re.compile(r"\.get\([^)]*\)\.[a-zA-Z_]\w*")
    for m in pat.finditer(code):
        out.append(_finding(
            "unchecked-get",
            "Possible unhandled None from .get()",
            m.group(0),
            "Pass a default (`.get('k', fallback)`) or check for None before attribute access.",
            severity="high",
        ))
    return out


DETECTORS = [
    detect_off_by_one,
    detect_bare_except,
    detect_except_pass,
    detect_mutable_default,
    detect_unchecked_get,
]


def scan(code: str) -> list[dict]:
    """Run every detector and return findings, deduped by (signature, evidence)."""
    seen: set[tuple[str, str]] = set()
    findings: list[dict] = []
    for det in DETECTORS:
        for f in det(code):
            key = (f["signature"], f["evidence"])
            if key not in seen:
                seen.add(key)
                findings.append(f)
    return findings
