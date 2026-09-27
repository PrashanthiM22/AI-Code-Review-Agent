"""
feature_extraction.py
----------------------
Turns the raw static-analysis output for a file into a fixed-size numeric
feature vector that the ML "bug risk" model can consume.

Feature order matters — train_model.py and ml_model.py both use this same
function, so the training data and the live prediction data always line up.
"""

FEATURE_NAMES = [
    "sloc",                 # source lines of code
    "comment_ratio",        # comments / sloc
    "avg_complexity",       # mean cyclomatic complexity across functions
    "max_complexity",       # worst function's cyclomatic complexity
    "num_functions",
    "pylint_issue_count",
    "bandit_issue_count",
    "high_severity_count",
    "medium_severity_count",
]


def extract_features(analysis_result: dict):
    """analysis_result is the dict returned by static_analysis.analyze_file()."""
    raw = analysis_result.get("raw_metrics", {}) or {}
    complexity_blocks = analysis_result.get("complexity", []) or []
    issues = analysis_result.get("issues", []) or []

    sloc = raw.get("sloc", 1) or 1  # avoid divide-by-zero
    comments = raw.get("comments", 0)
    comment_ratio = comments / sloc

    complexities = [b["complexity"] for b in complexity_blocks if b.get("complexity") is not None]
    avg_complexity = sum(complexities) / len(complexities) if complexities else 0
    max_complexity = max(complexities) if complexities else 0
    num_functions = len(complexity_blocks)

    pylint_count = sum(1 for i in issues if i["source"] == "pylint")
    bandit_count = sum(1 for i in issues if i["source"] == "bandit")
    high_count = sum(1 for i in issues if i["severity"] == "high")
    medium_count = sum(1 for i in issues if i["severity"] == "medium")

    return [
        sloc,
        round(comment_ratio, 3),
        round(avg_complexity, 2),
        max_complexity,
        num_functions,
        pylint_count,
        bandit_count,
        high_count,
        medium_count,
    ]
