"""
Rhodawk AI — GitHub App Authentication
=======================================
Short-lived installation tokens for enterprise multi-repo access.
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