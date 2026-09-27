# AI-Powered GitHub Code Review & Bug Detection Agent

A PBL project that reviews Python code for bugs, security issues, and code
quality problems, then scores each file's overall "bug risk" using a
locally trained machine-learning model — **no paid API key, no internet
LLM, and no GPU required.**

## How it works (architecture)

```
Input (GitHub repo URL / local folder / bundled sample)
        │
        ▼
[1] Ingestion          github_fetch.py — pulls .py files via the public GitHub REST API
        │
        ▼
[2] Static Analysis    static_analysis.py — runs pylint, bandit, radon (bugs,
        │              security issues, complexity) — fast, deterministic, offline
        ▼
[3] AI Risk Scoring    ml_model.py + train_model.py — a scikit-learn RandomForest,
        │              trained locally, scores each file's overall bug risk (0-100%)
        ▼
[4] Explanation Layer  explain.py — turns raw issue codes into plain-English
        │              explanations + suggested fixes
        ▼
[5] Interface          app.py — Streamlit dashboard: charts, per-file breakdown,
                       downloadable Markdown report
```

**Why no LLM API:** this build was made for a machine with no paid AI
subscription and 8GB RAM. Instead of calling GPT/Claude, the "AI" layer is a
real trained ML classifier (not a stub) plus a rule-based natural-language
explanation engine. This is a legitimate, common production pattern —
GitHub's own CodeQL and many commercial tools mix static analysis with a
lighter-weight scoring model rather than an LLM for every check.

## Setup (Windows, one-time)

```
cd ai-code-review-agent
pip install -r requirements.txt
python analyzer/train_model.py
```

The second command trains the bug-risk model on synthetic code samples
generated inside `train_model.py` and saves it to `model/bug_risk_model.pkl`.
Takes a few seconds, runs fine on an i3/8GB machine.

## Running it

```
streamlit run app.py
```

This opens a browser tab with the dashboard. In the sidebar, choose one of:

- **Built-in sample** — instant, no setup, analyzes the two files in `sample_repo/`
  (one deliberately buggy, one clean — good for a live demo comparison)
- **Public GitHub repo URL** — paste e.g. `https://github.com/owner/repo`
  (public repos only, no token needed, capped at 25 files to stay fast and
  within GitHub's free rate limit)
- **Local folder path** — point it at any folder of `.py` files on your machine

Click **Run Analysis**. You'll get: summary metrics, a severity chart, a
per-file risk chart, an expandable per-file issue table (line, severity,
plain-English explanation, suggested fix), and a downloadable Markdown report.

## New in this version

- **Far fewer GitHub API calls per repo scan.** The old version listed
  files folder-by-folder (1 API call per folder), which burned through the
  60/hour free limit fast on any multi-folder repo. It now fetches the
  entire file tree in a single API call, then downloads file contents from
  `raw.githubusercontent.com`, which has its own, much higher limit. A
  repo scan now costs about 2 GitHub API calls total, regardless of size.
- **Caching.** Re-running the same repo URL within 30 minutes reuses the
  cached result instead of calling GitHub again — free re-runs during a
  demo or while you're testing.
- **Upload files mode.** A fourth sidebar option lets you drag-and-drop
  `.py` files directly — no GitHub or internet needed at all. Good as a
  backup during a live presentation in case the venue's WiFi is unreliable.
- **Severity filter** on the per-file issue tables (show only High, only
  Medium, etc.).
- **Riskiest files leaderboard** — for repos with more than 3 files, the
  top 5 riskiest are shown at the top before the full file-by-file list.

## If you hit a "rate limit exceeded" error

Even with the improved fetch, GitHub allows only 60 unauthenticated API
requests/hour per IP address, shared across everyone on the same network —
easy to exhaust on shared college WiFi. Fix (free, 1 minute, no special
permissions):

1. Go to **github.com** → click your profile picture (top right) →
   **Settings**
2. Scroll to the bottom of the left sidebar → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token
   (classic)**
4. Give it any name (e.g. "code-review-agent"), leave all the permission
   checkboxes **unchecked** (you only need read access to public data,
   which needs no scopes at all), set an expiration (30 days is fine), and
   click **Generate token**
5. Copy the token (starts with `ghp_...`) — GitHub only shows it once
6. Paste it into the **"GitHub token (optional)"** field in the app's
   sidebar before clicking Run Analysis

This is a free GitHub token, unrelated to any paid AI API — it just proves
to GitHub which account is making the request so it gives you a higher
limit (5000/hour instead of 60).

## Project structure

```
ai-code-review-agent/
├── app.py                       # Streamlit interface (run this)
├── requirements.txt
├── analyzer/
│   ├── static_analysis.py       # pylint / bandit / radon wrapper
│   ├── feature_extraction.py    # code -> feature vector for the ML model
│   ├── train_model.py           # generates training data + trains the model
│   ├── ml_model.py              # loads the model, scores bug risk
│   ├── explain.py               # issue code -> plain English + fix
│   └── github_fetch.py          # pulls .py files from a public GitHub repo
├── model/
│   └── bug_risk_model.pkl       # created by train_model.py
└── sample_repo/
    ├── buggy_example.py         # deliberately buggy demo file
    └── clean_example.py         # clean demo file, for comparison
```

## For your presentation

1. **Problem** — manual code review is slow and inconsistent; plain static
   tools flag syntax issues but don't explain *why* something's risky or how
   risky a whole file is.
2. **Architecture diagram** — use the pipeline diagram above.
3. **Live demo** — run the built-in sample. `buggy_example.py` has a
   hardcoded password, a SQL injection pattern, a bare `except`, an `eval()`
   call, and deeply nested logic — show the tool catching all of it and
   scoring the file "High Risk," then show `clean_example.py` scoring "Low
   Risk" with zero issues, as a direct contrast.
4. **What's "AI" about it** — the RandomForest model looks at *patterns
   across* complexity, comment density, and issue counts to produce one risk
   score per file, rather than just listing individual line issues — that's
   the layer static analysis alone doesn't give you.
5. **Limitations (be upfront about these — examiners respect this)**
   - The ML model is trained on synthetic, self-generated code samples, not
     a large real-world labeled dataset — call this out as a scoping
     decision made for a time-boxed course project, and name it as the
     natural next step (train on a labeled real-world bug dataset).
   - Explanations are template-based (rule lookup by issue code), not
     model-generated free text — a deliberate trade-off to stay API-key-free
     and reliable in a live demo.
   - GitHub fetching is capped at 25 files and uses unauthenticated API
     access (~60 requests/hour limit) — fine for a demo repo, not for
     scanning a huge codebase.
6. **Future work** — swap the templated explanations for a real LLM call
   once API access is available (the function signature in `explain.py` is
   already designed for that swap); add GitHub Actions integration to run
   this automatically on every PR; train on a real bug-labeled dataset.
