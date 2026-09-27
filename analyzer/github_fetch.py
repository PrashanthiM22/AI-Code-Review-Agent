"""
github_fetch.py
----------------
Downloads .py files from a PUBLIC GitHub repository using only 1-2 calls
to the GitHub REST API, no matter how many folders the repo has.

Why this matters: the naive approach (list each folder one API call at a
time, recursively) burns through GitHub's 60-requests/hour free limit
almost instantly on any repo with more than a few folders. This version
instead:
  1. One call to get the repo's default branch
  2. One call to the "git trees" API with recursive=1, which returns the
     ENTIRE file listing of the repo in a single response
  3. Downloads actual file contents from raw.githubusercontent.com, which
     has a much higher, separate rate limit (not api.github.com's 60/hour)

An optional token still works and is recommended for private repos or if
you're on a shared network that's already used up the anonymous quota.
"""

import os
import re
import tempfile
import requests

API_ROOT = "https://api.github.com/repos"
RAW_ROOT = "https://raw.githubusercontent.com"
MAX_FILES = 25          # keep demos fast
MAX_FILE_SIZE_KB = 200  # skip huge generated files


def parse_repo_url(repo_url: str):
    """Accepts 'https://github.com/owner/repo' or 'owner/repo'."""
    repo_url = repo_url.strip().rstrip("/")
    match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
    if match:
        return match.group(1), match.group(2).replace(".git", "")
    if "/" in repo_url:
        owner, repo = repo_url.split("/", 1)
        return owner, repo
    raise ValueError("Could not parse a GitHub owner/repo from the input.")


def _auth_headers(token: str = None):
    return {"Authorization": f"token {token}"} if token else {}


def _raise_for_rate_limit(resp):
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError(
            "GitHub API rate limit exceeded. Add a free GitHub token in "
            "the sidebar to raise the limit from 60 to 5000 requests/hour "
            "(see README), or wait ~an hour for the limit to reset."
        )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("message", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"GitHub API error ({resp.status_code}): {msg}")


def _get_default_branch(owner, repo, token=None):
    resp = requests.get(f"{API_ROOT}/{owner}/{repo}", headers=_auth_headers(token), timeout=15)
    _raise_for_rate_limit(resp)
    return resp.json().get("default_branch", "main")


def _get_full_tree(owner, repo, branch, token=None):
    """One call, returns every file path in the repo (recursive)."""
    url = f"{API_ROOT}/{owner}/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=_auth_headers(token), timeout=20)
    _raise_for_rate_limit(resp)
    data = resp.json()
    return data.get("tree", [])


def fetch_repo_python_files(repo_url: str, token: str = None):
    """
    Downloads up to MAX_FILES .py files from a public repo into a temp
    directory, using only ~2 GitHub API calls regardless of repo size.
    Returns (local_dir, list_of_(repo_path, local_path)).
    """
    owner, repo = parse_repo_url(repo_url)
    branch = _get_default_branch(owner, repo, token)
    tree = _get_full_tree(owner, repo, branch, token)

    py_files = [
        item for item in tree
        if item.get("type") == "blob"
        and item["path"].endswith(".py")
        and item.get("size", 0) <= MAX_FILE_SIZE_KB * 1024
    ][:MAX_FILES]

    if not py_files:
        raise RuntimeError(
            "No .py files found in this repo. If it's not a Python "
            "project, try a different repo, or use 'Upload files' / "
            "'Local folder path' to scan whatever language it uses."
        )

    local_dir = tempfile.mkdtemp(prefix="repo_scan_")
    local_paths = []
    for item in py_files:
        raw_url = f"{RAW_ROOT}/{owner}/{repo}/{branch}/{item['path']}"
        content = requests.get(raw_url, timeout=15).text
        safe_name = item["path"].replace("/", "__")
        local_path = os.path.join(local_dir, safe_name)
        with open(local_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        local_paths.append((item["path"], local_path))

    return local_dir, local_paths
