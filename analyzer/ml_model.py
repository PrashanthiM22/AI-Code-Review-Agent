"""
ml_model.py
-----------
Loads the trained RandomForest ("bug risk") model and scores a file's
feature vector. This is the "AI" layer of the project: it looks at
patterns across complexity, comment density, and issue counts to flag
files that are risky as a whole, on top of the individual line-level
issues static analysis already found.
"""

import os
import joblib

_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model", "bug_risk_model.pkl",
)

_model_cache = None


def load_model():
    global _model_cache
    if _model_cache is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                "Model not found. Run `python analyzer/train_model.py` first."
            )
        _model_cache = joblib.load(_MODEL_PATH)
    return _model_cache


def predict_risk(features: list) -> dict:
    """Return a risk score (0-100) and label for one file's feature vector."""
    model = load_model()
    proba = model.predict_proba([features])[0]
    risk_score = round(proba[1] * 100, 1)  # probability of class "1" = risky

    if risk_score >= 66:
        label = "High Risk"
    elif risk_score >= 33:
        label = "Medium Risk"
    else:
        label = "Low Risk"

    return {"risk_score": risk_score, "label": label}
