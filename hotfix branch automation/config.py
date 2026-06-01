"""
Repository and Bitbucket workspace configuration.

Scale by adding entries to REPOS. Workspace: BITBUCKET_WORKSPACE in the
environment or a `.env` file (loaded by app.py / bitbucket_auth).
"""

import os
from typing import TypedDict


class RepoConfig(TypedDict):
    slug: str
    label: str


# Default workspace (Bitbucket Cloud). Override: export BITBUCKET_WORKSPACE=my-workspace
BITBUCKET_WORKSPACE: str = os.environ.get("BITBUCKET_WORKSPACE", "")

# Repos available in the UI dropdown (slug = repo slug in Bitbucket; workspace: franconnect)
REPOS: list[RepoConfig] = [
    {"slug": "data-replication-service", "label": "data-replication-service"},
    {"slug": "fcsky-common-lib", "label": "fcsky-common-lib"},
    {"slug": "fcsky-service-library", "label": "fcsky-service-library"},
    {"slug": "fcsky-service-registry", "label": "fcsky-service-registry"},
    {"slug": "fcsky-config-server", "label": "fcsky-config-server"},
    {"slug": "api-gateway", "label": "api-gateway"},
    {"slug": "release-audit-test", "label": "release-audit-test"},
    {"slug": "release-task-test", "label": "release-task-test"},
]

# Default production branch name
PROD_BRANCH: str = "prod"

# Release branch auto-name when override is empty:
# "full_month" -> release_april26 | "day_short_month" -> release_6may26
RELEASE_BRANCH_NAMING: str = "day_short_month"

# Hotfix suffix N = (Nth Wednesday of the calendar quarter) minus this many leading Wednesdays.
# 0 = first Wednesday of the quarter is .1. Use 1 when the first Wednesday is not numbered
# (2nd Wed = .1, 3rd = .2). Default 1 matches common “skip first weekly slot” practice.
HOTFIX_SKIP_LEADING_WEDNESDAYS: int = 1
