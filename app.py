"""
app.py
------
AI-Powered GitHub Code Review & Bug Detection Agent — Streamlit interface.

Run with:
    streamlit run app.py

No API keys or paid AI services are used anywhere in this project.
The "AI" layer is a locally trained scikit-learn model (see
analyzer/train_model.py) plus a rule-based explanation engine
(analyzer/explain.py) — both run entirely offline.
"""

import os
import shutil
import tempfile
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

from analyzer.static_analysis import analyze_file
from analyzer.feature_extraction import extract_features
from analyzer.ml_model import predict_risk
from analyzer.explain import explain_all
from analyzer.github_fetch import fetch_repo_python_files

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_repo")

st.set_page_config(page_title="AI Code Review Agent", page_icon="🛠️", layout="wide")


# ----------------------------------------------------------------------
# Cached GitHub fetch — re-running the same repo+token in this session
# costs zero extra API calls, which directly helps with the rate limit.
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=1800)
def cached_fetch_repo(repo_url: str, token: str):
    local_dir, file_pairs = fetch_repo_python_files(repo_url, token=token or None)
    # Read file contents into memory now, since the temp dir may not
    # survive across Streamlit's cached-function boundary reliably.
    contents = {}
    for repo_path, local_path in file_pairs:
        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
            contents[repo_path] = f.read()
    shutil.rmtree(local_dir, ignore_errors=True)
    return contents


# ----------------------------------------------------------------------
# Analysis pipeline
# ----------------------------------------------------------------------
def analyze_files(file_pairs):
    """file_pairs: list of (display_name, local_path). Returns results list."""
    results = []
    progress = st.progress(0.0, text="Starting analysis...")
    for idx, (display_name, local_path) in enumerate(file_pairs):
        progress.progress((idx + 1) / len(file_pairs), text=f"Analyzing {display_name}...")
        analysis = analyze_file(local_path)
        features = extract_features(analysis)
        try:
            risk = predict_risk(features)
        except FileNotFoundError:
            risk = {"risk_score": 0.0, "label": "Model not trained"}
        issues = explain_all(analysis["issues"])
        results.append({
            "file": display_name,
            "issues": issues,
            "risk": risk,
            "raw_metrics": analysis["raw_metrics"],
        })
    progress.empty()
    return results


def generate_markdown_report(results) -> str:
    lines = [f"# AI Code Review Report", f"Generated: {datetime.now():%Y-%m-%d %H:%M}\n"]
    total_issues = sum(len(r["issues"]) for r in results)
    lines.append(f"**Files analyzed:** {len(results)}  \n**Total issues found:** {total_issues}\n")

    ranked = sorted(results, key=lambda r: r["risk"]["risk_score"], reverse=True)
    lines.append("\n## Riskiest files\n")
    for r in ranked[:10]:
        lines.append(f"- `{r['file']}` — {r['risk']['label']} ({r['risk']['risk_score']}%)")

    for r in results:
        lines.append(f"\n## `{r['file']}`  —  Risk: **{r['risk']['label']}** "
                      f"({r['risk']['risk_score']}%)\n")
        if not r["issues"]:
            lines.append("_No issues found._\n")
            continue
        for issue in r["issues"]:
            lines.append(
                f"- **Line {issue['line']}** [{issue['severity'].upper()}] "
                f"`{issue['code']}` ({issue['source']})  \n"
                f"  {issue['explanation']}  \n"
                f"  *Suggested fix:* {issue['suggested_fix']}"
            )
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Sidebar — input selection
# ----------------------------------------------------------------------
st.sidebar.title("🛠️ Code Review Agent")
st.sidebar.caption("Static analysis + local ML risk model — no API key needed.")

mode = st.sidebar.radio(
    "Choose input source",
    ["Built-in sample (no setup)", "Public GitHub repo URL",
     "Upload files", "Local folder path"],
)

file_pairs = None
temp_dir_to_clean = None
upload_temp_dir = None

if mode == "Built-in sample (no setup)":
    st.sidebar.info("Uses the sample files bundled in `sample_repo/`.")
    if st.sidebar.button("Run Analysis", type="primary"):
        file_pairs = [
            (f, os.path.join(SAMPLE_DIR, f))
            for f in os.listdir(SAMPLE_DIR) if f.endswith(".py")
        ]

elif mode == "Public GitHub repo URL":
    repo_url = st.sidebar.text_input("Repo URL", placeholder="https://github.com/owner/repo")
    gh_token = st.sidebar.text_input(
        "GitHub token (optional)", type="password",
        help="Only needed if you hit a rate-limit error. Raises the limit "
             "from 60 to 5000 requests/hour. See README for how to generate "
             "one free — no cost, no special permissions needed.",
    )
    st.sidebar.caption(
        "Public repos only. Analyzes up to 25 .py files. Results for the "
        "same repo are cached for 30 minutes, so re-running costs no extra "
        "API calls."
    )
    if st.sidebar.button("Run Analysis", type="primary") and repo_url:
        with st.spinner("Fetching files from GitHub..."):
            try:
                contents = cached_fetch_repo(repo_url, gh_token or "")
                upload_temp_dir = tempfile.mkdtemp(prefix="repo_cached_")
                file_pairs = []
                for repo_path, code in contents.items():
                    local_path = os.path.join(upload_temp_dir, repo_path.replace("/", "__"))
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    file_pairs.append((repo_path, local_path))
                temp_dir_to_clean = upload_temp_dir
            except Exception as e:
                st.sidebar.error(f"Couldn't fetch repo: {e}")
                file_pairs = None

elif mode == "Upload files":
    uploaded = st.sidebar.file_uploader(
        "Upload one or more .py files", type=["py"], accept_multiple_files=True
    )
    st.sidebar.caption("No GitHub or internet needed — good backup for a live demo.")
    if st.sidebar.button("Run Analysis", type="primary") and uploaded:
        upload_temp_dir = tempfile.mkdtemp(prefix="upload_scan_")
        file_pairs = []
        for uf in uploaded:
            local_path = os.path.join(upload_temp_dir, uf.name)
            with open(local_path, "wb") as f:
                f.write(uf.getbuffer())
            file_pairs.append((uf.name, local_path))
        temp_dir_to_clean = upload_temp_dir

else:
    folder_path = st.sidebar.text_input("Local folder path", placeholder="C:\\path\\to\\project")
    if st.sidebar.button("Run Analysis", type="primary") and folder_path:
        if not os.path.isdir(folder_path):
            st.sidebar.error("That folder doesn't exist.")
        else:
            file_pairs = []
            for root, _, files in os.walk(folder_path):
                for fname in files:
                    if fname.endswith(".py"):
                        full = os.path.join(root, fname)
                        file_pairs.append((os.path.relpath(full, folder_path), full))
            file_pairs = file_pairs[:25]

# ----------------------------------------------------------------------
# Main area
# ----------------------------------------------------------------------
st.title("AI-Powered GitHub Code Review & Bug Detection Agent")
st.caption(
    "Pipeline: static analysis (pylint / bandit / radon) → ML bug-risk "
    "scoring (local scikit-learn model) → plain-English explanations."
)

if file_pairs:
    if not file_pairs:
        st.warning("No .py files found for the given input.")
    else:
        results = analyze_files(file_pairs)

        # ---- Overview metrics ----
        total_issues = sum(len(r["issues"]) for r in results)
        avg_risk = round(sum(r["risk"]["risk_score"] for r in results) / len(results), 1)
        high_risk_files = sum(1 for r in results if r["risk"]["label"] == "High Risk")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Files analyzed", len(results))
        c2.metric("Total issues", total_issues)
        c3.metric("Avg. risk score", f"{avg_risk}%")
        c4.metric("High-risk files", high_risk_files)

        # ---- Riskiest files leaderboard (useful once a repo has many files) ----
        if len(results) > 3:
            st.subheader("🏆 Riskiest files")
            ranked = sorted(results, key=lambda r: r["risk"]["risk_score"], reverse=True)[:5]
            lb_df = pd.DataFrame([
                {"File": r["file"], "Risk": r["risk"]["label"],
                 "Score": f"{r['risk']['risk_score']}%", "Issues": len(r["issues"])}
                for r in ranked
            ])
            st.dataframe(lb_df, use_container_width=True, hide_index=True)

        # ---- Charts ----
        col1, col2 = st.columns(2)
        with col1:
            sev_counts = {}
            for r in results:
                for issue in r["issues"]:
                    sev_counts[issue["severity"]] = sev_counts.get(issue["severity"], 0) + 1
            if sev_counts:
                fig = px.bar(
                    x=list(sev_counts.keys()), y=list(sev_counts.values()),
                    labels={"x": "Severity", "y": "Issue count"},
                    title="Issues by severity", color=list(sev_counts.keys()),
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            risk_df = pd.DataFrame(
                {"file": [r["file"] for r in results],
                 "risk_score": [r["risk"]["risk_score"] for r in results]}
            )
            fig2 = px.bar(risk_df, x="file", y="risk_score",
                          title="AI bug-risk score by file (%)", range_y=[0, 100])
            st.plotly_chart(fig2, use_container_width=True)

        # ---- Severity filter ----
        st.subheader("File-by-file review")
        severity_filter = st.multiselect(
            "Filter issues by severity", ["high", "medium", "low"],
            default=["high", "medium", "low"],
        )

        for r in results:
            badge = {"High Risk": "🔴", "Medium Risk": "🟠", "Low Risk": "🟢"}.get(
                r["risk"]["label"], "⚪"
            )
            visible_issues = [i for i in r["issues"] if i["severity"] in severity_filter]
            with st.expander(
                f"{badge} `{r['file']}` — {r['risk']['label']} ({r['risk']['risk_score']}%) "
                f"— {len(visible_issues)} issue(s) shown"
            ):
                if not visible_issues:
                    st.success("No issues match the current filter.")
                else:
                    df = pd.DataFrame([
                        {
                            "Line": i["line"], "Severity": i["severity"],
                            "Code": i["code"], "Source": i["source"],
                            "Explanation": i["explanation"],
                            "Suggested fix": i["suggested_fix"],
                        } for i in visible_issues
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)

        # ---- Download report ----
        report_md = generate_markdown_report(results)
        st.download_button(
            "⬇️ Download full report (Markdown)",
            data=report_md,
            file_name="ai_code_review_report.md",
            mime="text/markdown",
        )

        if temp_dir_to_clean and os.path.isdir(temp_dir_to_clean):
            shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
else:
    st.info("Choose an input source in the sidebar and click **Run Analysis** to begin.")
    st.markdown("""
    **What this tool does:**
    1. Fetches Python files (from a public GitHub repo, uploaded files, a local folder, or the bundled sample)
    2. Runs static analysis — `pylint`, `bandit`, `radon` — for bugs, security issues, and complexity
    3. Scores each file's overall bug-risk with a locally trained ML model (no API key)
    4. Explains each issue in plain English with a suggested fix
    5. Lets you filter by severity, see the riskiest files at a glance, and download a full report
    """)
