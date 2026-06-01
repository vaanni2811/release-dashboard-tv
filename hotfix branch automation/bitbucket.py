"""Bitbucket Cloud REST API (branches, tags, create branch)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from bitbucket_auth import BitbucketAuthError, create_session, get_bitbucket_auth

API_BASE = "https://api.bitbucket.org/2.0"

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = create_session()
    return _session


class BitbucketError(Exception):
    """API or configuration error."""


def require_credentials() -> None:
    try:
        get_bitbucket_auth()
    except BitbucketAuthError as e:
        raise BitbucketError(str(e)) from e


def _ref_encode(name: str) -> str:
    return quote(name, safe="")


def get_branch(workspace: str, repo_slug: str, branch_name: str) -> dict[str, Any] | None:
    """Return branch ref JSON or None if 404."""
    require_credentials()
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/refs/branches/{_ref_encode(branch_name)}"
    r = _get_session().get(url, timeout=60)
    if r.status_code == 404:
        return None
    if not r.ok:
        raise BitbucketError(f"Bitbucket error {r.status_code}: {r.text[:500]}")
    return r.json()


def get_tag(workspace: str, repo_slug: str, tag_name: str) -> dict[str, Any] | None:
    """Return tag ref JSON or None if 404."""
    require_credentials()
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/refs/tags/{_ref_encode(tag_name)}"
    r = _get_session().get(url, timeout=60)
    if r.status_code == 404:
        return None
    if not r.ok:
        raise BitbucketError(f"Bitbucket error {r.status_code}: {r.text[:500]}")
    return r.json()


def branch_exists(workspace: str, repo_slug: str, branch_name: str) -> bool:
    return get_branch(workspace, repo_slug, branch_name) is not None


def ref_commit_hash(ref_payload: dict[str, Any]) -> str:
    target = ref_payload.get("target") or {}
    h = target.get("hash")
    if not h:
        raise BitbucketError("Unexpected ref payload: missing target.hash")
    return str(h)


def resolve_source_hash(
    workspace: str,
    repo_slug: str,
    source_ref: str,
    source_kind: str,
) -> str:
    """
    Resolve a branch or tag name to a commit hash.
    source_kind: 'branch' | 'tag'
    """
    if source_kind == "tag":
        data = get_tag(workspace, repo_slug, source_ref)
        if data is None:
            raise BitbucketError(f"Tag not found: {source_ref}")
        return ref_commit_hash(data)
    if source_kind == "branch":
        data = get_branch(workspace, repo_slug, source_ref)
        if data is None:
            raise BitbucketError(f"Branch not found: {source_ref}")
        return ref_commit_hash(data)
    raise BitbucketError(f"Unknown source_kind: {source_kind}")


def list_all_branch_names(workspace: str, repo_slug: str) -> list[str]:
    """Paginate through refs/branches and return branch names."""
    require_credentials()
    names: list[str] = []
    url: str | None = f"{API_BASE}/repositories/{workspace}/{repo_slug}/refs/branches"
    params: dict[str, Any] = {"pagelen": 100}
    while url:
        r = _get_session().get(url, params=params if "?" not in url else None, timeout=60)
        if not r.ok:
            raise BitbucketError(f"Bitbucket error {r.status_code}: {r.text[:500]}")
        data = r.json()
        for item in data.get("values") or []:
            n = item.get("name")
            if n:
                names.append(str(n))
        url = (data.get("next") or "").strip() or None
        params = {}
    return names


def create_branch(
    workspace: str,
    repo_slug: str,
    branch_name: str,
    target_hash: str,
) -> dict[str, Any]:
    """POST /refs/branches — creates branch at target commit."""
    require_credentials()
    url = f"{API_BASE}/repositories/{workspace}/{repo_slug}/refs/branches"
    body = {"name": branch_name, "target": {"hash": target_hash}}
    r = _get_session().post(url, json=body, timeout=60)
    if not r.ok:
        raise BitbucketError(f"Create branch failed {r.status_code}: {r.text[:800]}")
    return r.json()
