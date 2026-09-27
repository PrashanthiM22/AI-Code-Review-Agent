"""
explain.py
----------
Turns a raw static-analysis issue code (like "W0702" or "B105") into a
plain-English explanation and a suggested fix. This is a deterministic,
template-based stand-in for an LLM explanation layer — it needs no API
key and no internet, which matters given the no-paid-API constraint on
this build. If you later get access to an LLM API, this is the exact
function to swap out (same input/output shape) for a model-generated
explanation instead of a templated one.
"""

_EXPLANATIONS = {
    # --- Pylint ---
    "W0702": ("A bare `except:` catches every possible error, including "
              "ones you didn't expect — this can hide real bugs.",
              "Catch a specific exception, e.g. `except ValueError:`."),
    "W0703": ("Catching the generic `Exception` class is almost as risky "
              "as a bare except — it can swallow serious errors.",
              "Catch the specific exception type you actually expect."),
    "W0611": ("An import is unused in this file.",
              "Remove the unused import to keep the file clean."),
    "W0612": ("A local variable is assigned but never used.",
              "Remove it, or use `_` if it's intentionally unused."),
    "E0602": ("This name is used but was never defined anywhere in scope.",
              "Check for a typo or a missing import/definition."),
    "W0102": ("A mutable default argument (like `[]` or `{}`) is reused "
              "across every call, which can cause hard-to-find bugs.",
              "Use `None` as the default and create the list/dict inside "
              "the function body."),
    "C0114": ("This module has no docstring explaining what it does.",
              "Add a short module-level docstring at the top of the file."),
    "C0116": ("This function has no docstring.",
              "Add a one-line docstring describing what it returns/does."),
    "R0912": ("This function has too many branches (deeply nested "
              "if/else), which makes it hard to read and easy to break.",
              "Split it into smaller helper functions."),

    # --- Bandit (security) ---
    "B105": ("A password or secret appears to be hardcoded directly in "
             "the source code.",
             "Load it from an environment variable or a secrets manager "
             "instead."),
    "B602": ("`os.system()`/subprocess is called with a string built from "
             "user input, which can allow command injection.",
             "Use `subprocess.run([...])` with a list of arguments, never "
             "a concatenated string."),
    "B608": ("A SQL query is built with string concatenation, which is "
             "vulnerable to SQL injection.",
             "Use parameterized queries, e.g. "
             "`cur.execute(\"... WHERE name = ?\", (username,))`."),
    "B307": ("`eval()` executes arbitrary code and is dangerous on any "
             "input that isn't fully trusted.",
             "Avoid `eval`; use `ast.literal_eval` for simple data, or "
             "redesign to avoid dynamic code execution."),
}

_DEFAULT_FIX = "Review this line and address the underlying issue reported by the tool."


def explain_issue(issue: dict) -> dict:
    """Attach a plain-English explanation + suggested fix to one issue dict."""
    code = issue.get("code", "")
    explanation, fix = _EXPLANATIONS.get(
        code, (issue.get("message", "A potential issue was flagged here."), _DEFAULT_FIX)
    )
    enriched = dict(issue)
    enriched["explanation"] = explanation
    enriched["suggested_fix"] = fix
    return enriched


def explain_all(issues: list) -> list:
    return [explain_issue(i) for i in issues]
