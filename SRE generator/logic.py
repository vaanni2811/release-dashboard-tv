"""Pure logic for SRE ticket generation (no UI or HTTP)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import config

_DIRECT_SYNC_MARKERS = (
    "(direct sync)",
    "[direct sync]",
    "(direct)",
    "[direct]",
    ", direct",
    ",direct",
)


class RepoBucket(str, Enum):
    RPM = "rpm"
    DIRECT_SYNC = "direct_sync"
    MSA = "msa"
    INTEGRATION = "integration"


@dataclass(frozen=True)
class ClassifiedRepos:
    include_rpm: bool
    direct_sync: tuple[str, ...]
    msa: tuple[str, ...]
    integration: tuple[str, ...]


@dataclass(frozen=True)
class TenantQuery:
    tenant: str
    queries: str


@dataclass
class SREInput:
    sre_type: str
    date_display: str
    repo_lines: list[str]
    cache_update_required: bool | None = None
    flush_msa_cache: bool = config.DEFAULT_FLUSH_MSA_CACHE
    hotfix_branch: str = ""
    uat_branch: str = config.DEFAULT_UAT_BRANCH
    fcsky_rpm: str = ""
    basethreads_fcsky_rpm: str = ""
    tomcat_fcsky_rpm: str = ""
    msa_image_tags: dict[str, str] = field(default_factory=dict)
    mysql_queries_all: list[str] = field(default_factory=list)
    mysql_queries_specific: list[TenantQuery] = field(default_factory=list)
    mysql_backup_required: bool = False
    mysql_backup_tables: str = ""
    psql_queries_all: list[str] = field(default_factory=list)
    psql_queries_specific: list[TenantQuery] = field(default_factory=list)


@dataclass(frozen=True)
class SRETicket:
    title: str
    description: str


def normalize_repo_name(raw: str) -> str:
    """Apply shorthand mapping and trim whitespace."""
    name = raw.strip()
    if not name:
        return ""
    key = name.lower()
    return config.SHORTHAND_MAPPING.get(key, name)


def is_excluded_repo(name: str) -> bool:
    """True if this repo must not appear anywhere in generated SRE output."""
    return name in config.EXCLUDED_FROM_SRE_REPOS


def _strip_direct_sync_marker(raw: str) -> tuple[str, bool]:
    text = raw.strip()
    explicit = False
    for marker in _DIRECT_SYNC_MARKERS:
        if text.lower().endswith(marker):
            text = text[: -len(marker)].strip().rstrip(",").strip()
            explicit = True
            break
    return text, explicit


def parse_repo_lines(lines: list[str]) -> list[tuple[str, bool]]:
    """
    Parse repo entries from UI/lines.

    Returns list of (normalized_repo_name, explicit_direct_sync).
    Order preserved; duplicates removed later during classification.
    """
    entries: list[tuple[str, bool]] = []
    for line in lines:
        for part in re.split(r"[\n,]+", line):
            part = part.strip()
            if not part or part.lower() in {"none", "n/a", "-"}:
                continue
            raw, explicit = _strip_direct_sync_marker(part)
            normalized = normalize_repo_name(raw)
            if normalized and not is_excluded_repo(normalized):
                entries.append((normalized, explicit))
    return entries


def parse_image_tags(text: str) -> dict[str, str]:
    """Parse ``repo:tag`` lines; tag may be empty."""
    tags: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            repo_part, tag_part = line.split(":", 1)
            repo = normalize_repo_name(repo_part.strip())
            if repo and not is_excluded_repo(repo):
                tags[repo] = tag_part.strip()
        else:
            repo = normalize_repo_name(line)
            if repo and not is_excluded_repo(repo):
                tags[repo] = ""
    return tags


def classify_repo(name: str, explicit_direct_sync: bool = False) -> RepoBucket:
    if name == config.FCSKY_REPO:
        return RepoBucket.RPM
    if name in config.INTEGRATION_STAGE_REPOS:
        return RepoBucket.INTEGRATION
    if explicit_direct_sync or name in config.DIRECT_SYNC_REPOS or name.endswith("-serverless"):
        return RepoBucket.DIRECT_SYNC
    return RepoBucket.MSA


def classify_repos(entries: list[tuple[str, bool]]) -> ClassifiedRepos:
    direct: list[str] = []
    msa: list[str] = []
    integration: list[str] = []
    include_rpm = False
    seen: set[str] = set()

    for name, explicit in entries:
        if name in seen:
            continue
        seen.add(name)

        bucket = classify_repo(name, explicit_direct_sync=explicit)
        if bucket == RepoBucket.RPM:
            include_rpm = True
        elif bucket == RepoBucket.DIRECT_SYNC:
            direct.append(name)
        elif bucket == RepoBucket.INTEGRATION:
            integration.append(name)
        else:
            msa.append(name)

    return ClassifiedRepos(
        include_rpm=include_rpm,
        direct_sync=tuple(direct),
        msa=tuple(msa),
        integration=tuple(integration),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _cache_update_default(sre_type: str) -> bool:
    return config.DEFAULT_CACHE_UPDATE.get(sre_type, True)


def _resolved_cache_update(data: SREInput) -> bool:
    if data.cache_update_required is not None:
        return data.cache_update_required
    return _cache_update_default(data.sre_type)


def _rpm_line(prefix: str, version: str) -> str:
    version = version.strip()
    base = prefix.rstrip("-")
    return f"{base}-{version}" if version else f"{base}-"


def _format_image_lines(repos: tuple[str, ...], tags: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for repo in repos:
        tag = tags.get(repo, "").strip()
        lines.append(f"{repo}:{tag}" if tag else f"{repo}:")
    return lines


def _section(header: str, body_lines: list[str]) -> str | None:
    if not body_lines:
        return None
    return header + "\n\n" + "\n".join(body_lines)


def _queries_block(header: str, body: str) -> str | None:
    text = body.strip()
    if not text or text.lower() in {"none", "n/a", "-"}:
        return None
    return header + "\n\n" + text


def parse_backup_table_names(raw: str) -> tuple[str, ...]:
    """Parse space-, comma-, or newline-separated backup table names."""
    names: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[\s,]+", raw.strip()):
        part = part.strip()
        if not part or part.lower() in {"none", "n/a", "-"}:
            continue
        if part not in seen:
            seen.add(part)
            names.append(part)
    return tuple(names)


def _mysql_query_body(queries: str, data: SREInput) -> str:
    """Queries text with optional backup-table line prepended."""
    query_text = queries.strip()
    if not query_text:
        return ""

    parts: list[str] = []
    if data.mysql_backup_required:
        tables = parse_backup_table_names(data.mysql_backup_tables)
        if tables:
            parts.append(f"Backup Table: {' '.join(tables)}")
    parts.append(query_text)
    return "\n\n".join(parts)


def _mysql_all_header(sre_type: str) -> str:
    if sre_type == config.SRE_TYPE_UAT:
        return "Kindly execute the below Mysql queries on all DEMO-UAT and MBE-UAT clusters:"
    return "Kindly execute the below Mysql queries on all Production clusters:"


def _mysql_specific_header(sre_type: str, tenant: str) -> str:
    return f"Kindly execute the below Mysql queries ONLY on {tenant}:"


def _psql_all_header(sre_type: str) -> str:
    if sre_type == config.SRE_TYPE_UAT:
        return "Kindly execute below PSQL queries on all DEMO/MBE UAT tenants:"
    return "Kindly execute below PSQL queries on all Production tenants:"


def _psql_specific_header(sre_type: str, tenant: str) -> str:
    if sre_type == config.SRE_TYPE_UAT:
        return f"Kindly execute below PSQL queries ONLY on {tenant}:"
    return f"Kindly execute below PSQL queries ONLY on {tenant}:"


def _append_query_sections(parts: list[str], data: SREInput) -> None:
    mysql_all_hdr = _mysql_all_header(data.sre_type)
    for queries in data.mysql_queries_all:
        body = _mysql_query_body(queries, data)
        block = _queries_block(mysql_all_hdr, body)
        if block:
            parts.extend([block, ""])

    for entry in data.mysql_queries_specific:
        tenant = entry.tenant.strip()
        if not tenant:
            continue
        body = _mysql_query_body(entry.queries, data)
        block = _queries_block(_mysql_specific_header(data.sre_type, tenant), body)
        if block:
            parts.extend([block, ""])

    psql_all_hdr = _psql_all_header(data.sre_type)
    for queries in data.psql_queries_all:
        block = _queries_block(psql_all_hdr, queries)
        if block:
            parts.extend([block, ""])

    for entry in data.psql_queries_specific:
        tenant = entry.tenant.strip()
        if not tenant:
            continue
        block = _queries_block(_psql_specific_header(data.sre_type, tenant), entry.queries)
        if block:
            parts.extend([block, ""])


def _build_rpm_lines(data: SREInput, classified: ClassifiedRepos) -> list[str]:
    has_rpm_numbers = bool(
        data.fcsky_rpm.strip()
        or data.basethreads_fcsky_rpm.strip()
        or data.tomcat_fcsky_rpm.strip()
    )
    if not classified.include_rpm and not has_rpm_numbers:
        return []

    lines = [
        _rpm_line("FCSKY", data.fcsky_rpm),
        _rpm_line("BaseThreadsFCSKY", data.basethreads_fcsky_rpm),
    ]
    if data.tomcat_fcsky_rpm.strip():
        lines.append(_rpm_line("tomcatFCSKY", data.tomcat_fcsky_rpm))
    return lines


def _append_flush_note(parts: list[str], flush: bool, *, uat: bool = False) -> None:
    if flush:
        label = "Notes" if uat else "Note"
        parts.append(f"{label}: Kindly flush msa cache.")


def _integration_stage_header(sre_type: str) -> str:
    if sre_type == config.SRE_TYPE_UAT:
        destination = "DEMO-UAT and MBE-UAT"
    else:
        destination = "all Production clusters"
    return (
        f"Kindly upload the image(s) below from Integration stage (prod branch) to {destination}:"
    )


def _append_direct_sync_production(
    parts: list[str], data: SREInput, classified: ClassifiedRepos
) -> None:
    if classified.direct_sync and data.hotfix_branch.strip():
        block = _section(
            f"Direct sync from {data.hotfix_branch.strip()} branch:",
            list(classified.direct_sync),
        )
        if block:
            parts.extend([block, ""])


def _append_direct_sync_uat(parts: list[str], data: SREInput, classified: ClassifiedRepos) -> None:
    branch = (data.uat_branch or config.DEFAULT_UAT_BRANCH).strip()
    if classified.direct_sync:
        block = _section(f"Direct sync from {branch} branch:", list(classified.direct_sync))
        if block:
            parts.extend([block, ""])


def _append_integration_stage_section(
    parts: list[str], data: SREInput, classified: ClassifiedRepos
) -> None:
    if not classified.integration:
        return
    lines = _format_image_lines(classified.integration, data.msa_image_tags)
    block = _section(_integration_stage_header(data.sre_type), lines)
    if block:
        parts.extend([block, ""])


def _generate_weekly(data: SREInput, classified: ClassifiedRepos) -> SRETicket:
    title = f"Upload weekly patches to Production | {data.date_display.strip()}"
    parts: list[str] = []

    rpm_lines = _build_rpm_lines(data, classified)
    if rpm_lines:
        parts.append(
            "Kindly upload the RPM from HP-APP to all PROD clusters as per the deployment days/time:"
        )
        parts.append("")
        parts.append(f"Cache update required: {_yes_no(_resolved_cache_update(data))}")
        parts.append("")
        parts.extend(rpm_lines)
        parts.append("")

    msa_lines = _format_image_lines(classified.msa, data.msa_image_tags)
    block = _section(
        "Kindly upload the MSA images below from HP ECS to Production:",
        msa_lines,
    )
    if block:
        parts.extend([block, ""])

    _append_direct_sync_production(parts, data, classified)
    _append_integration_stage_section(parts, data, classified)

    _append_query_sections(parts, data)

    _append_flush_note(parts, data.flush_msa_cache)
    return SRETicket(title=title, description="\n".join(parts).strip())


def _generate_urgent(data: SREInput, classified: ClassifiedRepos) -> SRETicket:
    title = f"Upload patch to Production | {data.date_display.strip()}"
    parts: list[str] = []

    rpm_lines = _build_rpm_lines(data, classified)
    if rpm_lines:
        parts.append("Kindly upload the RPM from HP-APP to ALL PROD clusters:")
        parts.append("")
        parts.append(f"Cache update required: {_yes_no(_resolved_cache_update(data))}")
        parts.append("")
        parts.extend(rpm_lines)
        parts.append("")

    msa_lines = _format_image_lines(classified.msa, data.msa_image_tags)
    block = _section(
        "Kindly upload the MSA images below from HP ECS to Production:",
        msa_lines,
    )
    if block:
        parts.extend([block, ""])

    _append_direct_sync_production(parts, data, classified)
    _append_integration_stage_section(parts, data, classified)

    _append_query_sections(parts, data)

    _append_flush_note(parts, data.flush_msa_cache)
    return SRETicket(title=title, description="\n".join(parts).strip())


def _generate_uat(data: SREInput, classified: ClassifiedRepos) -> SRETicket:
    title = f"Upload rpm from USTAGE to DEMO-UAT and MBE-UAT | {data.date_display.strip()}"
    parts: list[str] = []

    rpm_lines = _build_rpm_lines(data, classified)
    if rpm_lines:
        parts.append(
            "Kindly upload the RPM from USTAGE to DEMO-UAT and MBE-UAT clusters as per the deployment days/time:"
        )
        parts.append("")
        parts.append(f"Cache update required: {_yes_no(_resolved_cache_update(data))}")
        parts.append("")
        parts.extend(rpm_lines)
        parts.append("")

    msa_lines = _format_image_lines(classified.msa, data.msa_image_tags)
    block = _section(
        "Kindly upload the MSA images below from USTAGE to DEMO-UAT and MBE-UAT:",
        msa_lines,
    )
    if block:
        parts.extend([block, ""])

    _append_direct_sync_uat(parts, data, classified)
    _append_integration_stage_section(parts, data, classified)

    _append_query_sections(parts, data)

    _append_flush_note(parts, data.flush_msa_cache, uat=True)
    return SRETicket(title=title, description="\n".join(parts).strip())


def generate_ticket(data: SREInput) -> SRETicket:
    entries = parse_repo_lines(data.repo_lines)
    classified = classify_repos(entries)

    if data.sre_type == config.SRE_TYPE_WEEKLY:
        return _generate_weekly(data, classified)
    if data.sre_type == config.SRE_TYPE_URGENT:
        return _generate_urgent(data, classified)
    if data.sre_type == config.SRE_TYPE_UAT:
        return _generate_uat(data, classified)
    raise ValueError(f"Unknown SRE type: {data.sre_type!r}")


def format_full_ticket(ticket: SRETicket) -> str:
    """Body only — title is shown separately in Jira."""
    return ticket.description
