"""Streamlit UI for SRE ticket generator."""

from __future__ import annotations

import streamlit as st

import config
from logic import SREInput, TenantQuery, generate_ticket, parse_image_tags

_EMPTY_QUERY = {"", "none", "n/a", "-"}


def _cache_default_label(sre_type: str) -> str:
    default = config.DEFAULT_CACHE_UPDATE.get(sre_type, True)
    return "yes" if default else "no"


def _query_count_key(prefix: str) -> str:
    return f"sre_{prefix}_count"


def _init_query_count(prefix: str) -> int:
    key = _query_count_key(prefix)
    if key not in st.session_state:
        st.session_state[key] = 0
    return st.session_state[key]


def _render_all_tenant_queries(section_label: str, prefix: str, *, placeholder: str) -> list[str]:
    count = _init_query_count(prefix)
    st.markdown(f"**{section_label}**")
    values: list[str] = []
    for i in range(count):
        values.append(
            st.text_area(
                f"Query {i + 1}",
                key=f"sre_{prefix}_all_{i}",
                height=80,
                placeholder=placeholder,
            )
        )
    if st.button("+ Add query", key=f"sre_{prefix}_add_all"):
        st.session_state[_query_count_key(prefix)] = count + 1
        st.rerun()
    return [v.strip() for v in values if v.strip() and v.strip().lower() not in _EMPTY_QUERY]


def _render_tenant_queries(section_label: str, prefix: str, *, placeholder: str) -> list[TenantQuery]:
    count = _init_query_count(prefix)
    st.markdown(f"**{section_label}**")
    entries: list[TenantQuery] = []
    for i in range(count):
        tenant = st.text_input(f"Tenant/client {i + 1}", key=f"sre_{prefix}_tenant_{i}")
        queries = st.text_area(
            f"Queries for tenant {i + 1}",
            key=f"sre_{prefix}_queries_{i}",
            height=80,
            placeholder=placeholder,
        )
        entries.append(TenantQuery(tenant=tenant, queries=queries))
    if st.button("+ Add tenant query", key=f"sre_{prefix}_add_tenant"):
        st.session_state[_query_count_key(prefix)] = count + 1
        st.rerun()
    return [
        TenantQuery(tenant=e.tenant.strip(), queries=e.queries.strip())
        for e in entries
        if e.tenant.strip() and e.queries.strip() and e.queries.strip().lower() not in _EMPTY_QUERY
    ]


def _render_mysql_backup_options() -> tuple[bool, str]:
    st.markdown("**MySQL backup tables**")
    backup_required = st.checkbox(
        "Include backup table line for MySQL queries",
        key="sre_mysql_backup_required",
        help='Adds a line like: Backup Table: SUMMARY_DISPLAY FEATURE_CONFIGURATION',
    )
    backup_tables = ""
    if backup_required:
        backup_tables = st.text_input(
            "Backup table names (space or comma separated)",
            key="sre_mysql_backup_tables",
            placeholder="SUMMARY_DISPLAY FEATURE_CONFIGURATION",
        )
    return backup_required, backup_tables.strip()


def _render_query_sections(
    sre_type: str,
) -> tuple[list[str], list[TenantQuery], list[str], list[TenantQuery], bool, str]:
    st.subheader("Queries (optional)")
    mysql_backup_required, mysql_backup_tables = _render_mysql_backup_options()

    if sre_type == config.SRE_TYPE_UAT:
        all_mysql_label = "MySQL — all DEMO/MBE UAT tenants"
        tenant_mysql_label = "MySQL — specific tenant/client"
        all_psql_label = "PSQL — all DEMO/MBE UAT tenants"
        tenant_psql_label = "PSQL — specific tenant/client"
    else:
        all_mysql_label = "MySQL — all Production tenants"
        tenant_mysql_label = "MySQL — specific tenant/client"
        all_psql_label = "PSQL — all Production tenants"
        tenant_psql_label = "PSQL — specific tenant/client"

    mysql_all = _render_all_tenant_queries(
        all_mysql_label,
        "mysql_all",
        placeholder="UPDATE ...",
    )
    mysql_specific = _render_tenant_queries(
        tenant_mysql_label,
        "mysql_tenant",
        placeholder="UPDATE ...",
    )
    psql_all = _render_all_tenant_queries(
        all_psql_label,
        "psql_all",
        placeholder="UPDATE ...",
    )
    psql_specific = _render_tenant_queries(
        tenant_psql_label,
        "psql_tenant",
        placeholder="UPDATE ...",
    )
    return mysql_all, mysql_specific, psql_all, psql_specific, mysql_backup_required, mysql_backup_tables


def render() -> None:
    st.title("SRE Generator")
    st.caption("Generate ready-to-paste SRE/Jira ticket descriptions for patch deployments.")

    sre_type = st.selectbox("SRE type", options=list(config.SRE_TYPES), key="sre_type")

    is_production = sre_type in (config.SRE_TYPE_WEEKLY, config.SRE_TYPE_URGENT)
    is_uat = sre_type == config.SRE_TYPE_UAT

    date_label = "Date range" if sre_type == config.SRE_TYPE_WEEKLY else "Date"
    date_display = st.text_input(
        date_label,
        key="sre_date",
        placeholder="May/27 - May/30, 2026" if sre_type == config.SRE_TYPE_WEEKLY else "May/30, 2026",
    )

    st.subheader("Repositories")
    repo_text = st.text_area(
        "Repo list (one per line or comma-separated)",
        key="sre_repos",
        height=140,
        placeholder="fcsky\nfcsky-ui\nfcsky-cc\nunit-listing-service",
        help="Shorthand allowed (ui, cc, static, i18n, …). Mark direct sync: repo (direct sync)",
    )

    st.subheader("Deployment options")
    opt1, opt2 = st.columns(2)
    with opt1:
        cache_choice = st.selectbox(
            "Cache update required",
            options=["Use default", "yes", "no"],
            index=0,
            help=f"Default for this type: {_cache_default_label(sre_type)}",
            key="sre_cache_choice",
        )
    with opt2:
        flush_choice = st.selectbox(
            "Flush MSA cache",
            options=["yes", "no"],
            index=0,
            key="sre_flush_choice",
        )

    cache_update: bool | None
    if cache_choice == "Use default":
        cache_update = None
    else:
        cache_update = cache_choice == "yes"
    flush_msa_cache = flush_choice == "yes"

    st.subheader("RPM versions (optional)")
    r1, r2, r3 = st.columns(3)
    with r1:
        fcsky_rpm = st.text_input("FCSKY RPM version", key="sre_fcsky_rpm")
    with r2:
        basethreads_fcsky_rpm = st.text_input("BaseThreadsFCSKY RPM version", key="sre_basethreads_rpm")
    with r3:
        tomcat_fcsky_rpm = st.text_input("tomcatFCSKY RPM version", key="sre_tomcat_rpm")

    hotfix_branch = ""
    uat_branch = config.DEFAULT_UAT_BRANCH
    msa_tags_text = ""

    if is_production:
        st.subheader("Production details")
        hotfix_branch = st.text_input(
            "Hotfix branch",
            key="sre_hotfix_branch",
            placeholder="hotfix_r26q2.15",
        )
        msa_tags_text = st.text_area(
            "MSA / integration image tags (optional, one per line: repo:tag)",
            key="sre_msa_tags",
            height=100,
            placeholder="fcsky-commandcenter-service:1.2.3\nunit-listing-service:",
        )

    if is_uat:
        st.subheader("UAT details")
        uat_branch = st.text_input(
            "UAT branch",
            value=config.DEFAULT_UAT_BRANCH,
            key="sre_uat_branch",
        )
        msa_tags_text = st.text_area(
            "MSA image tags (optional, one per line: repo:tag)",
            key="sre_uat_msa_tags",
            height=100,
        )

    (
        mysql_all,
        mysql_specific,
        psql_all,
        psql_specific,
        mysql_backup_required,
        mysql_backup_tables,
    ) = _render_query_sections(sre_type)

    if st.button("Generate SRE ticket", type="primary", key="sre_generate"):
        if not date_display.strip():
            st.error(f"Enter a {date_label.lower()}.")
            st.stop()
        if not repo_text.strip():
            st.error("Enter at least one repository.")
            st.stop()
        if is_production and not hotfix_branch.strip() and any(
            marker in repo_text.lower()
            for marker in ("fcsky-ui", "fcsky-static", "fcsky-internationalization", "serverless", "direct")
        ):
            st.warning("Direct sync repos are listed but hotfix branch is empty — direct sync section will be omitted.")

        payload = SREInput(
            sre_type=sre_type,
            date_display=date_display.strip(),
            repo_lines=repo_text.splitlines(),
            cache_update_required=cache_update,
            flush_msa_cache=flush_msa_cache,
            hotfix_branch=hotfix_branch.strip(),
            uat_branch=uat_branch.strip() or config.DEFAULT_UAT_BRANCH,
            fcsky_rpm=fcsky_rpm.strip(),
            basethreads_fcsky_rpm=basethreads_fcsky_rpm.strip(),
            tomcat_fcsky_rpm=tomcat_fcsky_rpm.strip(),
            msa_image_tags=parse_image_tags(msa_tags_text),
            mysql_queries_all=mysql_all,
            mysql_queries_specific=mysql_specific,
            mysql_backup_required=mysql_backup_required,
            mysql_backup_tables=mysql_backup_tables,
            psql_queries_all=psql_all,
            psql_queries_specific=psql_specific,
        )
        ticket = generate_ticket(payload)

        st.subheader("Title")
        st.code(ticket.title, language=None)
        st.subheader("Description")
        st.code(ticket.description, language=None, wrap_lines=True)
