"""
static_analysis.py
-------------------
Runs deterministic static-analysis tools (pylint, bandit, radon) on a Python
file and normalizes their output into one common issue format:

    {
        "file": str,
        "line": int,
        "source": "pylint" | "bandit",
        "severity": "low" | "medium" | "high",
        "code": str,          # e.g. "C0114", "B105"
        "message": str,
    }

These tools are all fast, offline, and need no API key or internet access
(except to be pip-installed once). This is the "ground truth" layer the
ML risk model and the explanation layer build on top of.
"""

import json
import subprocess
import sys


PYLINT_SEVERITY = {
    "C": "low",       # Convention
    "R": "low",       # Refactor
    "W": "medium",    # Warning
    "E": "high",      # Error
    "F": "high",      # Fatal
}


def run_pylint(filepath: str):
    """Run pylint on a single file and return a normalized issue list."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pylint", filepath, "--output-format=json",
             "--disable=all",
             "--enable=C,E,W,F,unused-import,unused-variable,bare-except,"
             "broad-except,dangerous-default-value,undefined-variable"],
            capture_output=True, text=True, timeout=30
        )
        raw = result.stdout.strip()
        if not raw:
            return []
        data = json.loads(raw)
    except Exception:
        return []

    issues = []
    for item in data:
        code = item.get("message-id", "")
        severity = PYLINT_SEVERITY.get(code[:1], "low")
        issues.append({
            "file": filepath,
            "line": item.get("line", 0),
            "source": "pylint",
            "severity": severity,
            "code": code,
            "message": item.get("message", ""),
        })
    return issues


def run_bandit(filepath: str):
    """Run bandit (security scanner) on a single file."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-q", filepath],
            capture_output=True, text=True, timeout=30
        )
        raw = result.stdout.strip()
        if not raw:
            return []
        data = json.loads(raw)
    except Exception:
        return []

    issues = []
    for item in data.get("results", []):
        issues.append({
            "file": filepath,
            "line": item.get("line_number", 0),
            "source": "bandit",
            "severity": item.get("issue_severity", "LOW").lower(),
            "code": item.get("test_id", ""),
            "message": item.get("issue_text", "").strip(),
        })
    return issues


def run_radon_complexity(filepath: str):
    """Return cyclomatic complexity per function/method using radon."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc", filepath, "-j"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except Exception:
        return []

    blocks = data.get(filepath, [])
    return [
        {"name": b.get("name"), "complexity": b.get("complexity"),
         "line": b.get("lineno")}
        for b in blocks
    ]


def run_radon_raw(filepath: str):
    """Return raw size metrics (LOC, comments, blank lines) using radon."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "radon", "raw", filepath, "-j"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except Exception:
        return {}
    return data.get(filepath, {})


def analyze_file(filepath: str):
    """Run all static analysis tools on one file and combine the results."""
    pylint_issues = run_pylint(filepath)
    bandit_issues = run_bandit(filepath)
    complexity = run_radon_complexity(filepath)
    raw_metrics = run_radon_raw(filepath)

    return {
        "file": filepath,
        "issues": pylint_issues + bandit_issues,
        "complexity": complexity,
        "raw_metrics": raw_metrics,
    }
