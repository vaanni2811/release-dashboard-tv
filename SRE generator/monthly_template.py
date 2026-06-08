"""Monthly release SRE ticket template assembly."""

from __future__ import annotations

from dataclasses import dataclass

import config
from monthly_config import BOOTSTRAP_DEFAULT_TEXT

# Months using winter (Nov–Feb) mail timings.
_WINTER_MONTHS = frozenset({"November", "December", "January", "February"})

_ROLLBACK_PLAN = """Role-back Plan:
1 DB: Do keep MySQL and PG instance backups.
2 Repos: Do keep a record of earlier rpm of FCSKY, BT, and Tomcat FCSKY.
3 Do keep a record of the existing image no and backup (where the compilation is done) so that we can revert back to the Release (if any)
4 Revert configuration changes (if any)"""

_STATIC_NOTES = """Note:
1 Do keep MySQL and PG instance backups as well before starting any DB work.
tenantUpdationRequired flag value must be "no" in the APPLICATION_CONFIGURATION_DATA table.
UPDATE APPLICATION_CONFIGURATION_DATA SET KEY_VALUE='no' WHERE KEY_NAME = 'tenantUpdationRequired';
2 Update the necessary setting in Pingdom for build-down.
3 Cache update required: Yes (tomcat stop and start process as per cache update process).
4 Need to check the cluster-config.properties file to disable the Redis flag if tomcat started beyond the time mentioned in this file."""

_CLOSING_NOTES = """Note: Provide all the query execution logs in the ticket comments

Note:
Finally, restart Tomcat as per Cache: yes

After MSA works, kindly do flush the MSA cache through the back end.
Need to verify through manual script using get command, once the flush script has been executed for all respective production tenants

After UP of all tomcat and FJSSKY, Need to check and execute threads of FranNet, PhillyPretzelFactoryFINFTP,@franconnect.com OrangeTheoryFitnessDataCopyClientDatabaseScript.sh, SeniorHelpersnacha.sh, MerryMaidsFinancialDataFeed.sh , AmerispecFinancialDataFeed.sh tenants threads,extramileWhatsNew.sh, homehelpersWhats.sh
and execute manually (if not already executed)

@Ajeet Singh @Rohit Nigam @Mukesh Singla @utsav @udai : Kindly go through the mail and let us know in case of any concern.

@Amit Dixit :  Kindly approve the ticket accordingly.

Regards,
Release Panthers Team"""

_SERVICE_START_NOTE = """Note: Start respective services as well per the required order process

config-server (if a change in application.yml)
service-registry
api-gateway
auth-server
rest services"""


@dataclass
class MonthlyReleaseFields:
    release_code: str
    year: int
    month: str
    quarter_label: str
    date_range_display: str
    day_1_date: str
    day_2_date: str
    day_3_date: str
    form_generator_work: str
    form_generator_backup_table: str
    form_generator_query: str
    release_doc_suffix: str
    release_doc_link: str
    fcsky_config: str
    fcsky_config_details: str
    msa_config: str
    msa_config_details: str
    sso_enabled: bool
    sso_date: str
    sso_rpms: str
    patch_queries: str
    patch_queries_text: str
    release_query_path: str
    production_specific: str
    production_specific_text: str
    fc_go_specific: str
    fc_go_specific_text: str
    intl_cluster_queries: str
    intl_sql_file: str
    rest_cluster_date: str
    ref_sre_link: str
    pg_schema_path: str
    pg_patch: str
    pg_patch_text: str
    mongo: str
    mongo_path: str
    jobs_db: str
    jobs_db_text: str
    porting_jsp: str
    jsp_path: str
    audit_form: str
    bootstrapping: str
    bootstrapping_text: str
    fjs_changes: str
    fjs_rpm: str
    fjs_lib_rpm: str
    fjs_include_lib: bool
    fjs_date: str
    fjs_threads: str
    fjs_threads_date: str
    fjs_threads_ref: str
    base_ami: str
    base_ami_ref: str
    solr: str
    solr_date: str
    solr_ref: str


def monthly_title(fields: MonthlyReleaseFields) -> str:
    return (
        f"{fields.release_code} {fields.month} Release on Production with Patches | "
        f"{fields.date_range_display.strip()}"
    )


def _is_winter_month(month: str) -> bool:
    return month.strip() in _WINTER_MONTHS


def _mail_timings_block(fields: MonthlyReleaseFields) -> str:
    winter = _is_winter_month(fields.month)
    d1, d2, d3 = fields.day_1_date.strip(), fields.day_2_date.strip(), fields.day_3_date.strip()

    if winter:
        day1_times = (
            "EMEA Cluster: 8:30 AM\n"
            "Thurs Cluster: 9:30 AM\n"
            "APAC Cluster: 5:30 PM"
        )
        day2_time = "PROD-USA, API, Cluster 1, Cluster 2: 9:30 AM"
        day3_time = "INTL Clusters: 9:30 AM IST"
    else:
        day1_times = (
            "EMEA Cluster: 7:30 AM\n"
            "Thurs Cluster: 8:30 AM\n"
            "APAC Cluster: 6:30 PM"
        )
        day2_time = "PROD-USA, API, Cluster 1, Cluster 2: 8:30 AM"
        day3_time = "INTL Clusters: 8:30 AM IST"

    return (
        "@Imran Haque / SRE Team: Kindly process the below mail on production servers "
        "as per the below-scheduled downtime.\n\n"
        f"Mail Processing date: {d1}\n"
        f"Servers/start time (IST):\n{day1_times}\n\n"
        f"Mail Processing date: {d2}\n"
        f"{day2_time}\n\n"
        f"Mail Processing date: {d3}\n"
        f"{day3_time}"
    )


def _yes(fields_value: str) -> bool:
    return fields_value.strip().lower() == "yes"


def _na_or_yes_line(label: str, value: str) -> str:
    v = value.strip() or "NA"
    return f"{label}: {v}"


def _rpm_lines(fcsky: str, bt: str, tomcat: str) -> list[str]:
    lines: list[str] = []
    if tomcat.strip():
        lines.append(f"tomcatFCSKY-{tomcat.strip()}")
    if fcsky.strip():
        lines.append(f"FCSKY: FCSKY-{fcsky.strip()}")
    else:
        lines.append("FCSKY: ")
    if bt.strip():
        lines.append(f"BT: BaseThreadsFCSKY-{bt.strip()}")
    else:
        lines.append("BT: ")
    return lines


def _lines_from_text(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def build_monthly_description(
    fields: MonthlyReleaseFields,
    *,
    fcsky_rpm: str,
    basethreads_rpm: str,
    tomcat_rpm: str,
    msa_lines: list[str],
    integration_lines: list[str],
    direct_sync_repos: tuple[str, ...],
    serverless_repos: tuple[str, ...],
    mysql_blocks: list[str],
    psql_blocks: list[str],
) -> str:
    parts: list[str] = []

    parts.append(_mail_timings_block(fields))
    parts.append("")

    parts.append(_na_or_yes_line("Form Generator Work", fields.form_generator_work))
    if _yes(fields.form_generator_work):
        parts.append(
            "Note: Kindly do not down the Tomcat; first execute the below query to all databases "
            "and inform us so that we can execute the XML utility and inform back to you"
        )
        if fields.form_generator_query.strip():
            parts.append(fields.form_generator_query.strip())
    parts.append("")

    parts.append(_ROLLBACK_PLAN)
    parts.append("")
    parts.append(_STATIC_NOTES)
    parts.append("")

    doc_link = fields.release_doc_link.strip() or "<link>"
    parts.append(f"{fields.release_code} {fields.month} Release document: {doc_link}")
    parts.append("")

    parts.append("RPM upload branch details: prod branch from stage server to production server.")
    parts.append("")
    rpm_lines = _rpm_lines(fcsky_rpm, basethreads_rpm, tomcat_rpm)
    parts.extend(rpm_lines)
    parts.append("")

    parts.append(_na_or_yes_line("FCSKY Configuration Changes", fields.fcsky_config))
    if _yes(fields.fcsky_config) and fields.fcsky_config_details.strip():
        parts.append(fields.fcsky_config_details.strip())
    parts.append("")

    parts.append(_na_or_yes_line("MSA Configuration Changes", fields.msa_config))
    if _yes(fields.msa_config) and fields.msa_config_details.strip():
        parts.append(fields.msa_config_details.strip())
    parts.append("")

    if msa_lines:
        parts.append("MSA Work: Upload the MSA images to production from stage through the CICD pipeline:")
        parts.extend(msa_lines)
        parts.append("")

    if integration_lines:
        parts.append("Upload below service from integration stage to all production clusters:")
        parts.extend(integration_lines)
        parts.append("")

    if direct_sync_repos:
        parts.append(
            "Direct sync:  prod branch (after taking update of fcsky-common-lib and "
            "fcsky-service-library from prod branch)"
        )
        parts.extend(direct_sync_repos)
        parts.append("")

    if serverless_repos:
        parts.append("serverless sync list: (sync from prod branch)")
        parts.extend(serverless_repos)
    else:
        parts.append("serverless sync list: NA")
    parts.append("")

    if fields.sso_enabled and fields.sso_rpms.strip():
        sso_date = fields.sso_date.strip() or fields.day_3_date.strip()
        parts.append(f"SSO rpm from the prod branch to production: this will process on {sso_date}")
        parts.extend(_lines_from_text(fields.sso_rpms))
        parts.append("")

    parts.append(_SERVICE_START_NOTE)
    parts.append("")

    parts.append(
        "DB Script Work:\n"
        "Mysql: First, execute scripts to one MySQL database and PG schema. After cross-verifying "
        "the result of the first database, after then we proceed to execute it on other databases."
    )
    parts.append("")

    if _yes(fields.patch_queries) and fields.patch_queries_text.strip():
        parts.append("Patch queries:")
        parts.append(fields.patch_queries_text.strip())
    else:
        parts.append(_na_or_yes_line("Patch queries", fields.patch_queries))
    parts.append("")

    if fields.release_query_path.strip():
        parts.append("Release queries (from prod branch)")
        parts.append(fields.release_query_path.strip())
        parts.append("")

    parts.append(_na_or_yes_line("Production specific queries (if any)", fields.production_specific))
    if _yes(fields.production_specific) and fields.production_specific_text.strip():
        parts.append(fields.production_specific_text.strip())
    parts.append("")

    parts.append(_na_or_yes_line("FC_GO specific", fields.fc_go_specific))
    if _yes(fields.fc_go_specific) and fields.fc_go_specific_text.strip():
        parts.append(fields.fc_go_specific_text.strip())
    parts.append("")

    if fields.intl_cluster_queries.strip():
        sql_file = fields.intl_sql_file.strip() or "release.sql"
        parts.append(
            f"INTL Cluster Specific Queries: Execute below queries on INTL Cluster along with "
            f"{sql_file} on INTL processing day."
        )
        parts.append(fields.intl_cluster_queries.strip())
        parts.append("")

    if fields.rest_cluster_date.strip() or fields.ref_sre_link.strip():
        rest_date = fields.rest_cluster_date.strip() or fields.day_3_date.strip()
        ref = fields.ref_sre_link.strip() or "<link>"
        parts.append(
            f"Rest clusters these queries will execute by {rest_date} and restart the tomcat "
            f"with cache yes process through below SRE"
        )
        parts.append("")
        parts.append(f"Ref SRE: {ref}")
        parts.append("")

    if fields.pg_schema_path.strip():
        parts.append("PG schema work: (From prod branch)")
        parts.append(fields.pg_schema_path.strip())
        parts.append("")

    if _yes(fields.pg_patch) and fields.pg_patch_text.strip():
        parts.append("PG Patch queries:")
        parts.append(fields.pg_patch_text.strip())
    else:
        parts.append(_na_or_yes_line("PG Patch queries", fields.pg_patch))
    parts.append("")

    if _yes(fields.mongo) and fields.mongo_path.strip():
        parts.append("Mongo db query (prod branch) :")
        parts.append(fields.mongo_path.strip())
    else:
        parts.append(_na_or_yes_line("Mongo db query (prod branch)", fields.mongo))
    parts.append("")

    if _yes(fields.jobs_db) and fields.jobs_db_text.strip():
        parts.append("Jobs_db: (prod branch):")
        parts.append(fields.jobs_db_text.strip())
    else:
        parts.append(_na_or_yes_line("Jobs_db: (prod branch)", fields.jobs_db))
    parts.append("")

    if _yes(fields.porting_jsp):
        parts.append("Porting JSP : yes,")
        if fields.jsp_path.strip():
            parts.append(f"Jsp Path : {fields.jsp_path.strip()}")
    else:
        parts.append(_na_or_yes_line("Porting JSP", fields.porting_jsp))
    parts.append("")

    if _yes(fields.audit_form):
        parts.append("Audit Form Modification:yes  @Chahat Goyal @Amit Dixit")
    else:
        parts.append(_na_or_yes_line("Audit Form Modification", fields.audit_form))
    parts.append("")

    if _yes(fields.bootstrapping):
        bootstrap_text = fields.bootstrapping_text.strip() or BOOTSTRAP_DEFAULT_TEXT
        parts.append(f"Bootstrapping: yes,\n{bootstrap_text}")
    else:
        parts.append(_na_or_yes_line("Bootstrapping", fields.bootstrapping))
    parts.append("")

    if _yes(fields.fjs_changes):
        fjs_date = fields.fjs_date.strip() or fields.day_3_date.strip()
        parts.append(f"FJS Changes: Yes, process on {fjs_date}")
        if fields.fjs_include_lib:
            parts.append("Kindly upload the FJSSKY and fjssky-lib rpm to production from prod branch")
            parts.append(f"FJSSKY-LIB-{fields.fjs_lib_rpm.strip()}")
            parts.append(f"FJSSky-{fields.fjs_rpm.strip()}")
        else:
            parts.append("Kindly upload the FJSSKY rpm to production from prod branch")
            parts.append(f"FJSSky-{fields.fjs_rpm.strip()}")
    else:
        parts.append(_na_or_yes_line("FJS Changes", fields.fjs_changes))
    parts.append("")

    parts.append(_na_or_yes_line("FJS Threads changes", fields.fjs_threads))
    if _yes(fields.fjs_threads):
        threads_date = fields.fjs_threads_date.strip() or fields.day_3_date.strip()
        ref = fields.fjs_threads_ref.strip() or "<link>"
        parts.append(f"FJS Threads changes: (process after fjssky-lib rpm upload on {threads_date}")
        parts.append(f"Ref SRE: {ref}")
    parts.append("")

    parts.append(_na_or_yes_line("Base AMI Changes", fields.base_ami))
    if _yes(fields.base_ami) and fields.base_ami_ref.strip():
        parts.append(f"Ref Ticket: {fields.base_ami_ref.strip()}")
    parts.append("")

    parts.append(_na_or_yes_line("SOLR core creation and indexing", fields.solr))
    if _yes(fields.solr):
        solr_date = fields.solr_date.strip() or fields.day_3_date.strip()
        ref = fields.solr_ref.strip() or "<link>"
        parts.append(f"Only full indexing on {solr_date}")
        parts.append(f"Ref Ticket: {ref}")
    parts.append("")

    for block in mysql_blocks:
        parts.append(block)
        parts.append("")
    for block in psql_blocks:
        parts.append(block)
        parts.append("")

    parts.append(_CLOSING_NOTES)

    return "\n".join(parts).strip()
