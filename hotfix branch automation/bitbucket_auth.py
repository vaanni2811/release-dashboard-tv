"""
Bitbucket Cloud authentication for the REST API (requests).

Resolves credentials from environment variables in priority order:
repository access token, user API token (Basic), app password (Basic).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal, TypedDict

import requests

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None

if _load_dotenv is not None:
    _project_root = Path(__file__).resolve().parent.parent
    _load_dotenv(_project_root / ".env", override=False)

logger = logging.getLogger(__name__)

MISSING_CREDS_MSG = (
    "No Bitbucket credentials found. Set one of: BITBUCKET_TOKEN, "
    "BITBUCKET_API_TOKEN, or BITBUCKET_APP_PASSWORD"
)


class BitbucketAuthError(RuntimeError):
    """Raised when no usable Bitbucket credentials are configured."""


class BitbucketAuthBearer(TypedDict):
    type: Literal["bearer"]
    headers: dict[str, str]
    auth: None


class BitbucketAuthBasic(TypedDict):
    type: Literal["basic"]
    headers: dict[str, str]
    auth: tuple[str, str]


BitbucketAuthConfig = BitbucketAuthBearer | BitbucketAuthBasic


def get_bitbucket_auth() -> BitbucketAuthConfig:
    """
    Select the best available Bitbucket Cloud credential strategy from the environment.

    Priority:
        1. ``BITBUCKET_TOKEN`` — Bearer token (repository access token or compatible).
        2. ``BITBUCKET_EMAIL`` + ``BITBUCKET_API_TOKEN`` — HTTP Basic (email, API token).
        3. ``BITBUCKET_USERNAME`` + ``BITBUCKET_APP_PASSWORD`` — HTTP Basic.

    Incomplete pairs (e.g. API token without email) are skipped in favor of the next method.

    Returns:
        A dict with ``type`` ``\"bearer\"`` or ``\"basic\"``, ``headers`` for JSON API calls,
        and ``auth`` set to ``None`` for bearer or ``(user, secret)`` for basic.

    Raises:
        BitbucketAuthError: If no valid credential combination is present.
    """
    token = (os.environ.get("BITBUCKET_TOKEN") or "").strip()
    if token:
        return BitbucketAuthBearer(
            type="bearer",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth=None,
        )

    email = (os.environ.get("BITBUCKET_EMAIL") or "").strip()
    api_token = (os.environ.get("BITBUCKET_API_TOKEN") or "").strip()
    if email and api_token:
        return BitbucketAuthBasic(
            type="basic",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth=(email, api_token),
        )

    username = (os.environ.get("BITBUCKET_USERNAME") or "").strip()
    app_password = (os.environ.get("BITBUCKET_APP_PASSWORD") or "").strip()
    if username and app_password:
        return BitbucketAuthBasic(
            type="basic",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            auth=(username, app_password),
        )

    raise BitbucketAuthError(MISSING_CREDS_MSG)


def credentials_available() -> bool:
    """Return True if ``get_bitbucket_auth()`` would succeed (no logging)."""
    try:
        get_bitbucket_auth()
    except BitbucketAuthError:
        return False
    else:
        return True


def _log_selected_method(cfg: BitbucketAuthConfig) -> None:
    """Emit debug log for which credential path is in use."""
    if cfg["type"] == "bearer":
        logger.debug("Using Repository Token")
        return
    email = (os.environ.get("BITBUCKET_EMAIL") or "").strip()
    api_token = (os.environ.get("BITBUCKET_API_TOKEN") or "").strip()
    if email and api_token:
        logger.debug("Using API Token")
    else:
        logger.debug("Using App Password")


def create_session() -> requests.Session:
    """
    Build a ``requests.Session`` with Bitbucket auth applied.

    Bearer tokens are set on session headers; Basic auth uses ``session.auth``.
    """
    cfg = get_bitbucket_auth()
    _log_selected_method(cfg)

    session = requests.Session()
    session.headers.update(cfg["headers"])
    if cfg["type"] == "basic":
        session.auth = cfg["auth"]

    return session


__all__ = [
    "BitbucketAuthError",
    "MISSING_CREDS_MSG",
    "BitbucketAuthConfig",
    "create_session",
    "credentials_available",
    "get_bitbucket_auth",
]
