"""
Rhodawk AI — GitHub App Authentication + Fork-and-PR Mode
==========================================================
Handles authentication for:
  1. GitHub App (short-lived installation tokens) — enterprise mode
  2. Personal Access Token (PAT) — simple mode
  3. Fork-and-PR mode (antagonist) — forks any public repo, applies fix, opens cross-repo PR

Fork-and-PR mode enables Rhodawk to fix ANY public GitHub repository:
  - Fork target repo under the authenticated user account
  - Apply fix to the fork
  - Open a cross-repository PR to upstream

Enable fork mode: RHODAWK_FORK_MODE=true
Fork org/user:   RHODAWK_FORK_OWNER (defaults to authenticated user)
"""

import os
import time

import jwt
import requests


def get_installation_token(repo: str) -> str:
    app_id = os.getenv("RHODAWK_APP_ID")
    private_key = os.getenv("RHODAWK_APP_PRIVATE_KEY", "").replace("\\n", "\n")
    if not app_id or not private_key:
        raise EnvironmentError("RHODAWK_APP_ID and RHODAWK_APP_PRIVATE_KEY are required")

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }

    owner, repo_name = repo.split("/", 1)
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/installation",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    installation_id = resp.json()["id"]

    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def get_github_token(repo: str) -> str:
    if os.getenv("RHODAWK_APP_ID") and os.getenv("RHODAWK_APP_PRIVATE_KEY"):
        return get_installation_token(repo)
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise EnvironmentError("No GitHub App credentials or GITHUB_TOKEN configured")
    return token


def get_authenticated_user(token: str) -> str:
    """Return the login of the authenticated GitHub user."""
    resp = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("login", "")


def fork_repo(upstream_repo: str, token: str) -> str:
    """
    Fork upstream_repo to the authenticated user's account (or RHODAWK_FORK_OWNER org).
    Returns the full_name of the created fork (e.g. 'myuser/myrepo').
    Idempotent — if fork already exists, returns existing fork name.
    """
    fork_owner = os.getenv("RHODAWK_FORK_OWNER", "")
    owner, repo_name = upstream_repo.split("/", 1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }

    payload: dict = {}
    if fork_owner:
        payload["organization"] = fork_owner

    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo_name}/forks",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    fork_data = resp.json()
    fork_full_name = fork_data.get("full_name", "")

    # GitHub forks are async — wait up to 30s for it to be ready
    for _ in range(10):
        check = requests.get(
            f"https://api.github.com/repos/{fork_full_name}",
            headers=headers,
            timeout=10,
        )
        if check.status_code == 200:
            return fork_full_name
        time.sleep(3)

    return fork_full_name


def create_cross_repo_pr(
    upstream_repo: str,
    fork_full_name: str,
    branch: str,
    test_path: str,
    token: str,
) -> str:
    """
    Open a cross-repository PR from fork:branch → upstream:main.
    Returns the PR URL.
    """
    fork_owner = fork_full_name.split("/")[0]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }
    payload = {
        "title": f"[Rhodawk] Auto-heal: {os.path.basename(test_path)}",
        "head": f"{fork_owner}:{branch}",
        "base": "main",
        "body": (
            "## Rhodawk AI Autonomous Fix\n\n"
            "This PR was generated autonomously by Rhodawk AI.\n\n"
            "**Verification pipeline applied:**\n"
            "- Tests re-run and verified GREEN after fix\n"
            "- SAST gate (bandit + secret scan + semgrep) passed\n"
            "- Supply chain gate (typosquatting + CVE scan) passed\n"
            "- 3-model adversarial consensus review: APPROVED\n\n"
            f"**Test fixed:** `{test_path}`\n\n"
            "_Please review the diff carefully before merging._"
        ),
        "draft": False,
        "maintainer_can_modify": True,
    }
    resp = requests.post(
        f"https://api.github.com/repos/{upstream_repo}/pulls",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


def open_pr_for_repo(
    upstream_repo: str,
    branch: str,
    test_path: str,
    token: str,
    fork_mode: bool = False,
) -> str:
    """
    Unified PR creation:
      - If fork_mode=False (default): opens PR on the same repo (requires push access)
      - If fork_mode=True: forks the upstream repo and opens a cross-repo PR

    Returns PR URL.
    """
    if not fork_mode:
        from app import create_github_pr
        return create_github_pr(upstream_repo, branch, test_path, token)

    fork_full_name = fork_repo(upstream_repo, token)
    return create_cross_repo_pr(upstream_repo, fork_full_name, branch, test_path, token)
