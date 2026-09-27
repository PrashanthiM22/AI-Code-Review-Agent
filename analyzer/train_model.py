"""
train_model.py
---------------
Trains the "bug risk" classifier used by the AI reasoning layer.

No API key, no internet, no GPU needed — this is a small scikit-learn
RandomForest trained on synthetic code samples generated right here. It
runs in a few seconds on an i3/8GB laptop.

WHY SYNTHETIC DATA: there's no ready-made, labeled "buggy vs clean Python
file" dataset that ships with this project, so we generate a batch of
clean, well-written snippets and a batch of deliberately risky snippets
(hardcoded secrets, bare excepts, high complexity, no docstrings, etc.),
run them through the same static-analysis + feature-extraction pipeline
used at prediction time, and train on that. This is a legitimate and
common approach for a course project — just be upfront about it in your
report/demo (see README "Limitations").

Run this once before using the app:
    python analyzer/train_model.py
"""

import os
import sys
import tempfile
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.static_analysis import analyze_file
from analyzer.feature_extraction import extract_features

import joblib
from sklearn.ensemble import RandomForestClassifier


CLEAN_TEMPLATES = [
'''"""Utility module for {name}."""


def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


def is_even(n: int) -> bool:
    """Return True if n is even."""
    return n % 2 == 0
''',
'''"""A small, well-documented data class for {name}."""


class Point:
    """Represents a 2D point."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: "Point") -> float:
        """Euclidean distance to another point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
''',
'''"""Simple, safe file helper for {name}."""

import os


def read_file_safely(path: str) -> str:
    """Read a file and return its contents, or an empty string if missing."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
''',
'''"""Small statistics helpers for {name}."""


def mean(values):
    """Return the arithmetic mean of a list of numbers."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def variance(values):
    """Return the population variance of a list of numbers."""
    if not values:
        return 0.0
    avg = mean(values)
    return sum((v - avg) ** 2 for v in values) / len(values)
''',
]

BUGGY_TEMPLATES = [
'''import os

password = "SuperSecret123"


def run_command(user_input):
    os.system("echo " + user_input)


def divide(a, b):
    try:
        return a / b
    except:
        pass
''',
'''def process(data):
    result = []
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] > 0:
                if data[j] > 0:
                    if i != j:
                        if data[i] > data[j]:
                            result.append(data[i])
                        else:
                            result.append(data[j])
    unused_var = 42
    return result
''',
'''import sqlite3


def get_user(conn, username):
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()


def risky_eval(expr):
    return eval(expr)
''',
'''def calc(a, b, c, d, e, op):
    if op == 1:
        if a > 0:
            if b > 0:
                x = a + b
            else:
                x = a - b
        else:
            if c > 0:
                x = c + d
            else:
                x = c - d
    elif op == 2:
        x = e
    else:
        x = 0
    return x
''',
]


def _build_dataset(samples_per_template: int = 14):
    X, y = [], []
    with tempfile.TemporaryDirectory() as tmpdir:
        idx = 0
        for template in CLEAN_TEMPLATES:
            for _ in range(samples_per_template):
                idx += 1
                code = template.format(name=f"module_{idx}")
                path = os.path.join(tmpdir, f"clean_{idx}.py")
                with open(path, "w") as f:
                    f.write(code)
                features = extract_features(analyze_file(path))
                X.append(features)
                y.append(0)  # 0 = low risk

        for template in BUGGY_TEMPLATES:
            for _ in range(samples_per_template):
                idx += 1
                path = os.path.join(tmpdir, f"buggy_{idx}.py")
                with open(path, "w") as f:
                    f.write(template)
                features = extract_features(analyze_file(path))
                X.append(features)
                y.append(1)  # 1 = high risk

    return X, y


def train_and_save(model_path: str = None):
    if model_path is None:
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "model", "bug_risk_model.pkl",
        )

    print("Generating synthetic training samples and running static analysis...")
    X, y = _build_dataset()
    print(f"Training on {len(X)} samples ({sum(y)} risky, {len(y) - sum(y)} clean)...")

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=5, min_samples_leaf=2, random_state=42
    )
    clf.fit(X, y)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    random.seed(42)
    train_and_save()
