"""Configuration for SRE ticket generator."""

from __future__ import annotations

# SRE patch types shown in the UI.
SRE_TYPE_WEEKLY = "Weekly Production Patch"
SRE_TYPE_URGENT = "Urgent Production Patch"
SRE_TYPE_UAT = "DEMO/MBE UAT Patch"

SRE_TYPES: tuple[str, ...] = (SRE_TYPE_WEEKLY, SRE_TYPE_URGENT, SRE_TYPE_UAT)

# Repos listed in the form but omitted entirely from generated SRE tickets.
EXCLUDED_FROM_SRE_REPOS: frozenset[str] = frozenset(
    {
        "fcsky-common-lib",
        "fcsky-service-library",
    }
)

# Integration stage uploads (separate section; not MSA or direct sync).
INTEGRATION_STAGE_REPOS: frozenset[str] = frozenset(
    {
        "integration-auth-service",
        "integration-api-gateway",
        "integration-config-service",
        "integration-mgmt-admin",
        "integration-registry-service",
        "interim-data-replication-system",
    }
)

# Repos that always go under Direct Sync (after shorthand normalization).
DIRECT_SYNC_REPOS: frozenset[str] = frozenset(
    {
        "fcsky-ui",
        "fcsky-static-resources",
        "fcsky-internationalization",
    }
)

# Shorthand / typo → canonical repo name (lowercase keys).
SHORTHAND_MAPPING: dict[str, str] = {
    "cc": "fcsky-commandcenter-service",
    "fcsky-cc": "fcsky-commandcenter-service",
    "commandcenter": "fcsky-commandcenter-service",
    "ui": "fcsky-ui",
    "fcsky-ui": "fcsky-ui",
    "static": "fcsky-static-resources",
    "fcsky-static": "fcsky-static-resources",
    "fcsky-static-resources": "fcsky-static-resources",
    "fcsky-static-resoucres": "fcsky-static-resources",
    "i18": "fcsky-internationalization",
    "fcsky-i18": "fcsky-internationalization",
    "i18n": "fcsky-internationalization",
    "fcsky-i18n": "fcsky-internationalization",
    "fcsky-internationalization": "fcsky-internationalization",
    "internationalization": "fcsky-internationalization",
    "common-lib": "fcsky-common-lib",
    "fcsky-common-lib": "fcsky-common-lib",
    "service-lib": "fcsky-service-library",
    "service-library": "fcsky-service-library",
    "fcsky-service-library": "fcsky-service-library",
    "fcsky-service-lib": "fcsky-service-library",
    "common": "fcsky-common-service",
    "audit": "fcsky-audit-service",
    "task": "fcsky-task-service",
    "tenant-config": "fcsky-tenant-config",
    "integration-auth": "integration-auth-service",
    "auth": "integration-auth-service",
}

# Default cache update when the user leaves the field unspecified.
DEFAULT_CACHE_UPDATE: dict[str, bool] = {
    SRE_TYPE_WEEKLY: True,
    SRE_TYPE_URGENT: False,
    SRE_TYPE_UAT: True,
}

DEFAULT_FLUSH_MSA_CACHE: bool = True
DEFAULT_UAT_BRANCH: str = "uat"
FCSKY_REPO: str = "fcsky"
