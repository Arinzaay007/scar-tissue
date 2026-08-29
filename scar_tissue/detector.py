import re
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
        "off_by_one": {"name": "Off-by-one error", "severity": "high", "regex": [r"range\\(len\\((\\w+)\\)\\)"], "description": "Manual indexing with range(len(x)) is error-prone.", "fix": "Use enumerate()."},
        "manual_indexing": {"name": "Manual indexing", "severity": "medium", "regex": [r"(\\w+)\\[i\\]"], "description": "Use enumerate() for index + value.", "fix": "Use enumerate()."},
        "bare_except": {"name": "Bare except clause", "severity": "high", "regex": [r"except\\s*:"], "description": "Bare except catches everything.", "fix": "Catch specific exceptions."},
        "mutable_default": {"name": "Mutable default argument", "severity": "high", "regex": [r"def \\w+\\([^)]*=\\s*\\[", r"def \\w+\\([^)]*=\\s*\\{"], "description": "Mutable defaults are shared across calls.", "fix": "Use None as default."},
        "hardcoded_secret": {"name": "Hardcoded secret", "severity": "critical", "regex": [r"password\\s*=", r"secret\\s*=", r"api_key\\s*="], "description": "Hardcoded secrets are a security risk.", "fix": "Use environment variables."},
        "eval_usage": {"name": "eval() usage", "severity": "critical", "regex": [r"\\beval\\("], "description": "eval() executes arbitrary code.", "fix": "Use ast.literal_eval()."},
        "global_variable": {"name": "Global variable mutation", "severity": "medium", "regex": [r"global\\s+\\w+"], "description": "Global variables make code hard to test.", "fix": "Use a class."},
        "print_debug": {"name": "print() for debugging", "severity": "low", "regex": [r"^\\s*print\\("], "description": "Use logging instead of print().", "fix": "Replace with logging."},
    }

    def __init__(self):
        self.compiled = {}
        for k, p in self.PATTERNS.items():
            if p["regex"]:
                self.compiled[k] = {**p, "re": [re.compile(r) for r in p["regex"]]}

    def detect(self, code, file_path="<stdin>"):
        findings = []
        for i, line in enumerate(code.split("\n"), 1):
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
