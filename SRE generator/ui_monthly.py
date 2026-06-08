"""Monthly release ticket form fields."""

from __future__ import annotations

import streamlit as st

import config
from logic import classify_repos, parse_repo_lines
from monthly_dates import (
    default_processing_days,
    form_generator_query,
    processing_date_label,
    quarter_label,
    release_document_title,
    title_date_range,
)
from monthly_config import BOOTSTRAP_DEFAULT_TEXT, repos_include_fjs, repos_include_fjssky_lib
from monthly_template import MonthlyReleaseFields
from ui_monthly_config import render_fcsky_config_section, render_msa_config_section


def _yes_na(key: str, label: str, *, default: str = "NA") -> str:
    return st.selectbox(label, options=list(config.YES_NA_OPTIONS), index=0 if default == "NA" else 1, key=key)


def render_monthly_fields() -> MonthlyReleaseFields:
    st.subheader("Release schedule")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        release_code = st.selectbox("Release", options=list(config.RELEASE_CODES), key="mr_release_code")
    with c2:
        quarter = st.selectbox("Quarter", options=list(config.RELEASE_QUARTERS), key="mr_quarter")
    with c3:
        year = st.selectbox("Year", options=list(config.RELEASE_YEARS), index=1, key="mr_year")
    with c4:
        month = st.selectbox("Month", options=list(config.RELEASE_MONTHS), key="mr_month")

    computed_quarter_label = quarter_label(release_code, quarter)

    st.markdown("**Processing days** (Wed → Thu → Sat)")
    st.caption("Pick all three dates — calendars jump to the selected month; title and mail dates update automatically.")
    schedule_anchor = f"{year}|{month}"
    if st.session_state.get("mr_schedule_anchor") != schedule_anchor:
        day_wed_default, day_thu_default, day_sat_default = default_processing_days(int(year), month)
        st.session_state["mr_day_wed"] = day_wed_default
        st.session_state["mr_day_thu"] = day_thu_default
        st.session_state["mr_day_sat"] = day_sat_default
        st.session_state["mr_schedule_anchor"] = schedule_anchor
    elif "mr_day_wed" not in st.session_state:
        day_wed_default, day_thu_default, day_sat_default = default_processing_days(int(year), month)
        st.session_state["mr_day_wed"] = day_wed_default
        st.session_state["mr_day_thu"] = day_thu_default
        st.session_state["mr_day_sat"] = day_sat_default
        st.session_state["mr_schedule_anchor"] = schedule_anchor

    d1, d2, d3 = st.columns(3)
    with d1:
        day_wed = st.date_input("Day 1 — Wednesday", key="mr_day_wed")
    with d2:
        day_thu = st.date_input("Day 2 — Thursday", key="mr_day_thu")
    with d3:
        day_sat = st.date_input("Day 3 — Saturday", key="mr_day_sat")

    date_range = title_date_range(day_wed, day_thu, day_sat)
    day_1 = processing_date_label(day_wed)
    day_2 = processing_date_label(day_thu)
    day_3 = processing_date_label(day_sat)
    release_doc_suffix = release_document_title(release_code, month, date_range)

    st.info(f"**Title date range:** {date_range}")
    st.caption(f"Quarter label: **{computed_quarter_label}** · Release doc: **{release_doc_suffix}**")

    with st.expander("Release document", expanded=False):
        release_doc_link = st.text_input("Deployment plan link", key="mr_doc_link", placeholder="https://...")

    with st.expander("Form generator work", expanded=False):
        form_gen = _yes_na("mr_form_gen", "Form Generator Work")
        backup_table = ""
        form_query = ""
        if form_gen == "yes":
            backup_table = st.text_input(
                "Backup table suffix",
                key="mr_form_backup",
                placeholder="JUN26",
                help="Used in CREATE TABLE CLIENT_XMLS_BKP_<suffix>",
            )
            if st.session_state.get("mr_form_backup_last") != backup_table:
                st.session_state["mr_form_query"] = form_generator_query(backup_table)
                st.session_state["mr_form_backup_last"] = backup_table
            form_query = st.text_area(
                "Form generator query",
                key="mr_form_query",
                height=80,
            )

    with st.expander("RPM & configuration", expanded=True):
        r1, r2, r3 = st.columns(3)
        with r1:
            st.text_input("FCSKY RPM", key="sre_fcsky_rpm", placeholder="17.1.1-4092")
        with r2:
            st.text_input("BaseThreadsFCSKY RPM", key="sre_basethreads_rpm", placeholder="17.1.1-4092")
        with r3:
            st.text_input("tomcatFCSKY RPM (optional)", key="sre_tomcat_rpm", placeholder="20.1.1-138")

        fcsky_cfg, fcsky_cfg_details = render_fcsky_config_section()
        msa_cfg, msa_cfg_details = render_msa_config_section()

    st.subheader("Repositories")
    st.text_area(
        "Repo list (one per line; optional repo:tag for MSA/integration)",
        key="sre_repos",
        height=160,
        placeholder=(
            "fcsky\nfcsky-ui\nfcsky-tenant-config:prod_951f3ff_588\n"
            "integration-auth-service:prod_a49f633_39\n"
            "kb-entity-sync-serverless\nfcsky-auth-server"
        ),
        help=(
            "Auto-classified for monthly release: MSA services, direct sync (ui/static/i18n), "
            "serverless (*-serverless + fcsky-auth-server), integration stage repos."
        ),
    )
    repo_preview = st.session_state.get("sre_repos", "").strip()
    if repo_preview:
        classified = classify_repos(
            parse_repo_lines(repo_preview.splitlines()),
            config.SRE_TYPE_MONTHLY,
        )
        st.caption(
            f"MSA ({len(classified.msa)}) · Direct sync ({len(classified.direct_sync)}) · "
            f"Serverless ({len(classified.serverless)}) · Integration ({len(classified.integration)})"
        )
        if classified.msa:
            st.markdown("**MSA:** " + ", ".join(classified.msa))
        if classified.direct_sync:
            st.markdown("**Direct sync:** " + ", ".join(classified.direct_sync))
        if classified.serverless:
            st.markdown("**Serverless:** " + ", ".join(classified.serverless))
        if classified.integration:
            st.markdown("**Integration stage:** " + ", ".join(classified.integration))

    with st.expander("SSO (optional)", expanded=False):
        sso_enabled = st.checkbox("Include SSO RPM section", key="mr_sso_enabled")
        sso_date = ""
        sso_rpms = ""
        if sso_enabled:
            sso_date = st.text_input("SSO processing date", key="mr_sso_date", placeholder=day_3)
            sso_rpms = st.text_area(
                "SSO RPMs",
                key="mr_sso_rpms",
                height=60,
                placeholder="tomcatSSOMediator-15.0.0-16.rpm\nSSOMediator-14.0.0-22.rpm",
            )

    with st.expander("DB scripts", expanded=True):
        patch_q = _yes_na("mr_patch_q", "Patch queries")
        patch_q_text = ""
        if patch_q == "yes":
            patch_q_text = st.text_area("Patch queries", key="mr_patch_q_text", height=80)

        release_query_path = st.text_input(
            "Release query path (prod branch)",
            key="mr_release_sql",
            placeholder="FranConnect/DBScripts/UpgradeScripts/R26/feb26/feb26.sql",
        )

        prod_spec = _yes_na("mr_prod_spec", "Production specific queries")
        prod_spec_text = ""
        if prod_spec == "yes":
            prod_spec_text = st.text_area("Production specific queries", key="mr_prod_spec_text", height=100)

        fc_go = _yes_na("mr_fc_go", "FC_GO specific")
        fc_go_text = ""
        if fc_go == "yes":
            fc_go_text = st.text_area("FC_GO specific SQL files", key="mr_fc_go_text", height=100)

        intl_queries = st.text_area(
            "INTL cluster specific queries",
            key="mr_intl_queries",
            height=100,
            placeholder="DELETE FROM SOLR_ENGINE_TABLES where...",
        )
        ic1, ic2 = st.columns(2)
        with ic1:
            intl_sql_file = st.text_input("INTL SQL file name", key="mr_intl_sql", placeholder="apr26.sql")
        with ic2:
            rest_cluster_date = st.text_input("Rest clusters date", key="mr_rest_date", placeholder=day_3)
        ref_sre = st.text_input("Ref SRE link (rest clusters)", key="mr_ref_sre", placeholder="https://...")

        pg_schema = st.text_input(
            "PG schema path",
            key="mr_pg_schema",
            placeholder="fcsky-tenant-config/src/main/resources/dbscripts/UpgradeScripts/R25/nov25/nov25.sql",
        )
        pg_patch = _yes_na("mr_pg_patch", "PG Patch queries")
        pg_patch_text = ""
        if pg_patch == "yes":
            pg_patch_text = st.text_area("PG patch queries", key="mr_pg_patch_text", height=80)

        mongo = _yes_na("mr_mongo", "Mongo db query")
        mongo_path = ""
        if mongo == "yes":
            mongo_path = st.text_input(
                "Mongo script path",
                key="mr_mongo_path",
                placeholder="fcsky-tenant-config/.../mongodb.ai-integration-db/ai-integration.js",
            )

        jobs_db = _yes_na("mr_jobs_db", "Jobs_db")
        jobs_db_text = ""
        if jobs_db == "yes":
            jobs_db_text = st.text_area(
                "Jobs_db details",
                key="mr_jobs_db_text",
                height=80,
                placeholder="Keep jobs_db backup before executing...\nfcsky-tenant-config/.../jobsdb_feb26.sql",
            )

    with st.expander("Optional sections", expanded=False):
        porting = _yes_na("mr_porting", "Porting JSP")
        jsp_path = ""
        if porting == "yes":
            jsp_path = st.text_input("JSP path", key="mr_jsp_path", placeholder="$build_URL$/fc/documentCentralizationPorting.jsp")

        audit = _yes_na("mr_audit", "Audit Form Modification")
        bootstrap = _yes_na("mr_bootstrap", "Bootstrapping")
        bootstrap_text = BOOTSTRAP_DEFAULT_TEXT if bootstrap == "yes" else ""

        repo_text = st.session_state.get("sre_repos", "")
        fjs_from_repos = repos_include_fjs(repo_text)
        fjs_include_lib = repos_include_fjssky_lib(repo_text)
        fjs_rpm = ""
        fjs_lib_rpm = ""
        fjs_date = ""
        if fjs_from_repos:
            fjs = "yes"
            fjs_date = day_3
            st.caption(f"**FJS Changes:** yes (from repo list) — process on {day_3}")
            fjs_rpm = st.text_input("FJSSky RPM version", key="mr_fjs_rpm", placeholder="17.0.0-1155")
            if fjs_include_lib:
                fjs_lib_rpm = st.text_input(
                    "FJSSKY-LIB RPM version",
                    key="mr_fjs_lib_rpm",
                    placeholder="17.0.0.00-87",
                )
        else:
            fjs = _yes_na("mr_fjs", "FJS Changes")
            if fjs == "yes":
                fjs_date = st.text_input("FJS processing date", key="mr_fjs_date", placeholder=day_3)
                fjs_rpm = st.text_input("FJSSky RPM version", key="mr_fjs_rpm", placeholder="17.0.0-1155")
                if fjs_include_lib:
                    fjs_lib_rpm = st.text_input(
                        "FJSSKY-LIB RPM version",
                        key="mr_fjs_lib_rpm",
                        placeholder="17.0.0.00-87",
                    )

        fjs_threads = _yes_na("mr_fjs_threads", "FJS Threads changes")
        fjs_threads_date = ""
        fjs_threads_ref = ""
        if fjs_threads == "yes":
            fjs_threads_date = day_3
            st.caption(f"FJS threads processing date: {day_3}")
            fjs_threads_ref = st.text_input("FJS threads Ref SRE", key="mr_fjs_threads_ref")

        base_ami = _yes_na("mr_base_ami", "Base AMI Changes")
        base_ami_ref = ""
        if base_ami == "yes":
            base_ami_ref = st.text_input("Base AMI ref ticket", key="mr_base_ami_ref")

        solr = _yes_na("mr_solr", "SOLR core creation and indexing")
        solr_date = ""
        solr_ref = ""
        if solr == "yes":
            solr_date = day_3
            st.caption(f"SOLR indexing date: {day_3}")
            solr_ref = st.text_input("SOLR ref ticket", key="mr_solr_ref")

    return MonthlyReleaseFields(
        release_code=release_code,
        year=int(year),
        month=month,
        quarter_label=computed_quarter_label,
        date_range_display=date_range,
        day_1_date=day_1,
        day_2_date=day_2,
        day_3_date=day_3,
        form_generator_work=form_gen,
        form_generator_backup_table=backup_table,
        form_generator_query=form_query,
        release_doc_suffix=release_doc_suffix,
        release_doc_link=release_doc_link,
        fcsky_config=fcsky_cfg,
        fcsky_config_details=fcsky_cfg_details,
        msa_config=msa_cfg,
        msa_config_details=msa_cfg_details,
        sso_enabled=sso_enabled,
        sso_date=sso_date,
        sso_rpms=sso_rpms,
        patch_queries=patch_q,
        patch_queries_text=patch_q_text,
        release_query_path=release_query_path,
        production_specific=prod_spec,
        production_specific_text=prod_spec_text,
        fc_go_specific=fc_go,
        fc_go_specific_text=fc_go_text,
        intl_cluster_queries=intl_queries,
        intl_sql_file=intl_sql_file,
        rest_cluster_date=rest_cluster_date,
        ref_sre_link=ref_sre,
        pg_schema_path=pg_schema,
        pg_patch=pg_patch,
        pg_patch_text=pg_patch_text,
        mongo=mongo,
        mongo_path=mongo_path,
        jobs_db=jobs_db,
        jobs_db_text=jobs_db_text,
        porting_jsp=porting,
        jsp_path=jsp_path,
        audit_form=audit,
        bootstrapping=bootstrap,
        bootstrapping_text=bootstrap_text,
        fjs_changes=fjs,
        fjs_rpm=fjs_rpm,
        fjs_lib_rpm=fjs_lib_rpm,
        fjs_include_lib=fjs_include_lib,
        fjs_date=fjs_date,
        fjs_threads=fjs_threads,
        fjs_threads_date=fjs_threads_date,
        fjs_threads_ref=fjs_threads_ref,
        base_ami=base_ami,
        base_ami_ref=base_ami_ref,
        solr=solr,
        solr_date=solr_date,
        solr_ref=solr_ref,
    )
