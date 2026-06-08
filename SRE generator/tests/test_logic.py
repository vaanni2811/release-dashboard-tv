"""Unit tests for SRE ticket generator logic."""

from __future__ import annotations

import unittest

import config
from logic import (
    ClassifiedRepos,
    SREInput,
    TenantQuery,
    classify_repos,
    classify_repo,
    format_full_ticket,
    generate_ticket,
    is_serverless_repo,
    normalize_repo_name,
    parse_backup_table_names,
    parse_repo_lines,
)
from monthly_template import MonthlyReleaseFields


class TestShorthand(unittest.TestCase):
    def test_typo_static_resources(self) -> None:
        self.assertEqual(normalize_repo_name("fcsky-static-resoucres"), "fcsky-static-resources")

    def test_static_aliases_direct_sync(self) -> None:
        from logic import RepoBucket

        for alias in ("static", "fcsky-static", "fcsky-static-resources"):
            name = normalize_repo_name(alias)
            self.assertEqual(name, "fcsky-static-resources")
            self.assertEqual(classify_repo(name), RepoBucket.DIRECT_SYNC)

    def test_ui_aliases_direct_sync(self) -> None:
        from logic import RepoBucket

        for alias in ("ui", "fcsky-ui"):
            name = normalize_repo_name(alias)
            self.assertEqual(name, "fcsky-ui")
            self.assertEqual(classify_repo(name), RepoBucket.DIRECT_SYNC)

    def test_i18_aliases_direct_sync(self) -> None:
        from logic import RepoBucket

        for alias in ("i18", "fcsky-i18", "fcsky-internationalization"):
            name = normalize_repo_name(alias)
            self.assertEqual(name, "fcsky-internationalization")
            self.assertEqual(classify_repo(name), RepoBucket.DIRECT_SYNC)

    def test_cc_aliases(self) -> None:
        self.assertEqual(normalize_repo_name("fcsky-cc"), "fcsky-commandcenter-service")
        self.assertEqual(normalize_repo_name("cc"), "fcsky-commandcenter-service")

    def test_excluded_repo_shorthands(self) -> None:
        self.assertEqual(normalize_repo_name("common-lib"), "fcsky-common-lib")
        self.assertEqual(normalize_repo_name("service-lib"), "fcsky-service-library")
        self.assertEqual(normalize_repo_name("service-library"), "fcsky-service-library")


class TestIntegrationStage(unittest.TestCase):
    def test_integration_auth_shorthand(self) -> None:
        self.assertEqual(normalize_repo_name("integration-auth"), "integration-auth-service")

    def test_integration_section_after_direct_sync_production(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=[
                "fcsky-ui",
                "integration-auth",
                "unit-listing-service",
            ],
            hotfix_branch="hotfix_r26q2.15",
            msa_image_tags={"integration-auth-service": "3.2.1"},
        )
        ticket = generate_ticket(data)
        self.assertNotIn("integration-auth-service", ticket.description.split("MSA images")[1].split("Direct sync")[0])
        direct_idx = ticket.description.index("Direct sync")
        integration_idx = ticket.description.index("Integration stage")
        self.assertLess(direct_idx, integration_idx)
        self.assertIn(
            "Kindly upload the image(s) below from Integration stage (prod branch) to all Production clusters:",
            ticket.description,
        )
        self.assertIn("integration-auth-service:3.2.1", ticket.description)
        self.assertNotIn("unit-listing-service", ticket.description.split("Integration stage")[1].split("Note:")[0])

    def test_integration_section_uat_destination(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_UAT,
            date_display="May/30, 2026",
            repo_lines=["integration-api-gateway"],
        )
        ticket = generate_ticket(data)
        self.assertIn(
            "Kindly upload the image(s) below from Integration stage (prod branch) to DEMO-UAT and MBE-UAT:",
            ticket.description,
        )
        self.assertIn("integration-api-gateway:", ticket.description)

    def test_interim_data_replication_not_msa(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_URGENT,
            date_display="May/30, 2026",
            repo_lines=["interim-data-replication-system", "unit-listing-service"],
        )
        ticket = generate_ticket(data)
        self.assertIn("interim-data-replication-system:", ticket.description)
        self.assertIn("Integration stage", ticket.description)


class TestExcludedRepos(unittest.TestCase):
    def test_excluded_repos_omitted_from_ticket(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=[
                "fcsky",
                "fcsky-common-lib",
                "common-lib",
                "fcsky-service-library",
                "service-lib",
                "unit-listing-service",
            ],
            hotfix_branch="hotfix_r26q2.15",
            msa_image_tags={
                "fcsky-common-lib": "1.0.0",
                "unit-listing-service": "2.0.1",
            },
        )
        ticket = generate_ticket(data)
        self.assertNotIn("fcsky-common-lib", ticket.description)
        self.assertNotIn("fcsky-service-library", ticket.description)
        self.assertNotIn("common-lib", ticket.description)
        self.assertNotIn("service-lib", ticket.description)
        self.assertIn("unit-listing-service:2.0.1", ticket.description)

    def test_excluded_only_does_not_add_empty_msa_section(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["common-lib", "service-library"],
            hotfix_branch="hotfix_r26q2.15",
        )
        ticket = generate_ticket(data)
        self.assertNotIn("MSA images", ticket.description)
        self.assertNotIn("Direct sync", ticket.description)
        self.assertNotIn("RPM from HP-APP", ticket.description)


class TestClassification(unittest.TestCase):
    def test_fcsky_is_rpm_only(self) -> None:
        self.assertEqual(classify_repo("fcsky"), classify_repo("fcsky"))

    def test_direct_sync_known(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("fcsky-ui"), RepoBucket.DIRECT_SYNC)

    def test_serverless_suffix_non_monthly(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("foo-serverless"), RepoBucket.DIRECT_SYNC)

    def test_serverless_suffix_monthly_bucket(self) -> None:
        from logic import RepoBucket

        self.assertEqual(
            classify_repo("foo-serverless", sre_type=config.SRE_TYPE_MONTHLY),
            RepoBucket.SERVERLESS,
        )

    def test_auth_server_monthly_vs_weekly(self) -> None:
        from logic import RepoBucket

        self.assertEqual(
            classify_repo("fcsky-auth-server", sre_type=config.SRE_TYPE_MONTHLY),
            RepoBucket.SERVERLESS,
        )
        self.assertEqual(classify_repo("fcsky-auth-server"), RepoBucket.DIRECT_SYNC)

    def test_monthly_repo_segregation(self) -> None:
        lines = [
            "fcsky-ui",
            "fcsky-tenant-config",
            "kb-entity-sync-serverless",
            "fcsky-auth-server",
            "integration-auth-service",
        ]
        c = classify_repos(parse_repo_lines(lines), config.SRE_TYPE_MONTHLY)
        self.assertEqual(c.direct_sync, ("fcsky-ui",))
        self.assertEqual(c.msa, ("fcsky-tenant-config",))
        self.assertEqual(
            c.serverless,
            ("kb-entity-sync-serverless", "fcsky-auth-server"),
        )
        self.assertEqual(c.integration, ("integration-auth-service",))

    def test_monthly_fjs_repos_excluded_from_msa(self) -> None:
        lines = ["fcsky-tenant-config", "fjssky", "fjssky-lib", "fjs", "fjssky:26.0.0-1253"]
        c = classify_repos(parse_repo_lines(lines), config.SRE_TYPE_MONTHLY)
        self.assertEqual(c.msa, ("fcsky-tenant-config",))

    def test_parse_repo_lines_strips_image_tag(self) -> None:
        entries = parse_repo_lines(["fcsky-tenant-config:prod_951f3ff_588", "fjssky:26.0.0-1253"])
        self.assertEqual(entries, [("fcsky-tenant-config", False), ("fjssky", False)])

    def test_weekly_serverless_in_direct_sync(self) -> None:
        lines = ["fcsky-ui", "kb-entity-sync-serverless", "fcsky-auth-server"]
        c = classify_repos(parse_repo_lines(lines), config.SRE_TYPE_WEEKLY)
        self.assertEqual(c.serverless, ())
        self.assertEqual(
            c.direct_sync,
            ("fcsky-ui", "kb-entity-sync-serverless", "fcsky-auth-server"),
        )

    def test_integration_stage_repos(self) -> None:
        from logic import RepoBucket

        for repo in config.INTEGRATION_STAGE_REPOS:
            self.assertEqual(classify_repo(repo), RepoBucket.INTEGRATION)

    def test_unknown_integration_prefix_is_msa(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("integration-unknown-service"), RepoBucket.MSA)

    def test_example_repos(self) -> None:
        lines = [
            "fcsky",
            "fcsky-commandcenter-service",
            "unit-listing-service",
            "unit-listing-service",
            "fcsky-static-resoucres",
            "fcsky-cc",
            "fcsky-ui",
        ]
        c = classify_repos(parse_repo_lines(lines))
        self.assertTrue(c.include_rpm)
        self.assertEqual(
            c.direct_sync,
            ("fcsky-static-resources", "fcsky-ui"),
        )
        self.assertEqual(
            c.msa,
            ("fcsky-commandcenter-service", "unit-listing-service"),
        )


class TestWeeklyExample(unittest.TestCase):
    def test_user_example_output(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/27 - May/30, 2026",
            repo_lines=[
                "fcsky",
                "fcsky-commandcenter-service",
                "unit-listing-service",
                "unit-listing-service",
                "fcsky-static-resoucres",
                "fcsky-cc",
                "fcsky-ui",
            ],
            hotfix_branch="hotfix_r26q2.15",
        )
        ticket = generate_ticket(data)
        self.assertEqual(
            ticket.title,
            "Upload weekly patches to Production | May/27 - May/30, 2026",
        )
        expected = """Kindly upload the RPM from HP-APP to all PROD clusters as per the deployment days/time:

Cache update required: yes

FCSKY-
BaseThreadsFCSKY-

Kindly upload the MSA images below from HP ECS to Production:

fcsky-commandcenter-service:
unit-listing-service:

Direct sync from hotfix_r26q2.15 branch:

fcsky-static-resources
fcsky-ui

Note: Kindly flush msa cache."""
        self.assertEqual(ticket.description, expected)


class TestDefaults(unittest.TestCase):
    def test_urgent_cache_default_no(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_URGENT,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
        )
        ticket = generate_ticket(data)
        self.assertIn("Cache update required: no", ticket.description)

    def test_flush_can_be_disabled(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            flush_msa_cache=False,
        )
        ticket = generate_ticket(data)
        self.assertNotIn("flush msa cache", ticket.description.lower())

    def test_rpm_versions_when_provided(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            fcsky_rpm="9.1.2",
            basethreads_fcsky_rpm="9.1.2",
        )
        ticket = generate_ticket(data)
        self.assertIn("FCSKY-9.1.2", ticket.description)
        self.assertIn("BaseThreadsFCSKY-9.1.2", ticket.description)

    def test_msa_with_tag(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["unit-listing-service"],
            msa_image_tags={"unit-listing-service": "2.0.1"},
        )
        ticket = generate_ticket(data)
        self.assertIn("unit-listing-service:2.0.1", ticket.description)

    def test_tomcat_rpm_when_provided(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            tomcat_fcsky_rpm="9.1.2",
        )
        ticket = generate_ticket(data)
        self.assertIn("tomcatFCSKY-9.1.2", ticket.description)

    def test_omit_empty_sections(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["unit-listing-service"],
        )
        ticket = generate_ticket(data)
        self.assertNotIn("Direct sync", ticket.description)
        self.assertNotIn("RPM from HP-APP", ticket.description)

    def test_uat_notes_label(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_UAT,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
        )
        ticket = generate_ticket(data)
        self.assertIn("Notes: Kindly flush msa cache.", ticket.description)

    def test_multiple_mysql_and_psql_blocks(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_WEEKLY,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            mysql_queries_all=["SELECT 1;", "SELECT 2;"],
            mysql_queries_specific=[TenantQuery("clientA", "UPDATE a;")],
            psql_queries_all=["SELECT pg;"],
            psql_queries_specific=[TenantQuery("clientB", "UPDATE b;")],
        )
        ticket = generate_ticket(data)
        self.assertEqual(
            ticket.description.count(
                "Kindly execute the below Mysql queries on all Production clusters:"
            ),
            2,
        )
        self.assertIn("Kindly execute the below Mysql queries ONLY on clientA:", ticket.description)
        self.assertIn("UPDATE a;", ticket.description)
        self.assertIn("Kindly execute below PSQL queries ONLY on clientB:", ticket.description)

    def test_uat_mysql_psql_headers(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_UAT,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            mysql_queries_all=["SELECT 1;"],
            psql_queries_all=["SELECT 2;"],
        )
        ticket = generate_ticket(data)
        self.assertIn(
            "Kindly execute the below Mysql queries on all DEMO-UAT and MBE-UAT clusters:",
            ticket.description,
        )
        self.assertIn("Kindly execute below PSQL queries on all DEMO/MBE UAT tenants:", ticket.description)

    def test_mysql_backup_table_line(self) -> None:
        queries = (
            "INSERT INTO SUMMARY_DISPLAY(DISPLAY_NAME) VALUES ('x');\n\n"
            "DELETE FROM FEATURE_CONFIGURATION WHERE FEATURE_NAME='x';"
        )
        data = SREInput(
            sre_type=config.SRE_TYPE_UAT,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
            mysql_queries_all=[queries],
            mysql_backup_required=True,
            mysql_backup_tables="SUMMARY_DISPLAY, FEATURE_CONFIGURATION",
        )
        ticket = generate_ticket(data)
        self.assertIn("Backup Table: SUMMARY_DISPLAY FEATURE_CONFIGURATION", ticket.description)
        self.assertLess(
            ticket.description.index("Backup Table:"),
            ticket.description.index("INSERT INTO SUMMARY_DISPLAY"),
        )

    def test_parse_backup_table_names(self) -> None:
        self.assertEqual(
            parse_backup_table_names("SUMMARY_DISPLAY, FEATURE_CONFIGURATION"),
            ("SUMMARY_DISPLAY", "FEATURE_CONFIGURATION"),
        )


def _sample_monthly_fields(**overrides) -> MonthlyReleaseFields:
    base = dict(
        release_code="R26",
        year=2026,
        month="March",
        quarter_label="R26Q2",
        date_range_display="March/11 - March/14, 2026",
        day_1_date="Mar/11, 2026",
        day_2_date="Mar/12, 2026",
        day_3_date="Mar/14, 2026",
        release_doc_suffix="R26 March Release document (March/11 - March/14, 2026)",
        form_generator_work="NA",
        form_generator_backup_table="",
        form_generator_query="",
        release_doc_link="https://example.com/plan",
        fcsky_config="NA",
        fcsky_config_details="",
        msa_config="NA",
        msa_config_details="",
        sso_enabled=False,
        sso_date="",
        sso_rpms="",
        patch_queries="NA",
        patch_queries_text="",
        release_query_path="FranConnect/DBScripts/UpgradeScripts/R26/mar26/mar26.sql",
        production_specific="NA",
        production_specific_text="",
        fc_go_specific="NA",
        fc_go_specific_text="",
        intl_cluster_queries="",
        intl_sql_file="",
        rest_cluster_date="",
        ref_sre_link="",
        pg_schema_path="",
        pg_patch="NA",
        pg_patch_text="",
        mongo="NA",
        mongo_path="",
        jobs_db="NA",
        jobs_db_text="",
        porting_jsp="NA",
        jsp_path="",
        audit_form="NA",
        bootstrapping="NA",
        bootstrapping_text="",
        fjs_changes="NA",
        fjs_rpm="",
        fjs_lib_rpm="",
        fjs_include_lib=False,
        fjs_date="",
        fjs_threads="NA",
        fjs_threads_date="",
        fjs_threads_ref="",
        base_ami="NA",
        base_ami_ref="",
        solr="NA",
        solr_date="",
        solr_ref="",
    )
    base.update(overrides)
    return MonthlyReleaseFields(**base)


class TestMonthlyRelease(unittest.TestCase):
    def test_title_format(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Mar/11 - Mar/14, 2026",
            repo_lines=["fcsky-ui"],
            fcsky_rpm="17.1.1-4092",
            basethreads_fcsky_rpm="17.1.1-4092",
            monthly=_sample_monthly_fields(),
        )
        ticket = generate_ticket(data)
        self.assertEqual(
            ticket.title,
            "R26 March Release on Production with Patches | March/11 - March/14, 2026",
        )

    def test_standard_month_timings(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Mar/11 - Mar/14, 2026",
            repo_lines=[],
            monthly=_sample_monthly_fields(month="March"),
        )
        ticket = generate_ticket(data)
        self.assertIn("EMEA Cluster: 7:30 AM", ticket.description)
        self.assertIn("PROD-USA, API, Cluster 1, Cluster 2: 8:30 AM", ticket.description)
        self.assertIn("INTL Clusters: 8:30 AM IST", ticket.description)

    def test_winter_month_timings(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Feb/11 - Feb/14, 2026",
            repo_lines=[],
            monthly=_sample_monthly_fields(month="February"),
        )
        ticket = generate_ticket(data)
        self.assertIn("EMEA Cluster: 8:30 AM", ticket.description)
        self.assertIn("APAC Cluster: 5:30 PM", ticket.description)
        self.assertIn("INTL Clusters: 9:30 AM IST", ticket.description)

    def test_direct_sync_msa_serverless_sections(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Mar/11 - Mar/14, 2026",
            repo_lines=[
                "fcsky-ui",
                "fcsky-tenant-config:prod_951f3ff_588",
                "kb-entity-sync-serverless",
                "fcsky-auth-server",
            ],
            fcsky_rpm="17.1.1-4092",
            basethreads_fcsky_rpm="17.1.1-4092",
            monthly=_sample_monthly_fields(),
        )
        ticket = generate_ticket(data)
        self.assertIn("Direct sync:", ticket.description)
        self.assertIn("fcsky-ui", ticket.description)
        self.assertNotIn("fcsky-auth-server", ticket.description.split("Direct sync")[1].split("serverless")[0])
        self.assertIn("MSA Work:", ticket.description)
        self.assertIn("fcsky-tenant-config:prod_951f3ff_588", ticket.description)
        self.assertIn("serverless sync list:", ticket.description)
        self.assertIn("kb-entity-sync-serverless", ticket.description)
        self.assertIn("fcsky-auth-server", ticket.description)
        self.assertIn("Release Panthers Team", ticket.description)

    def test_is_serverless_repo(self) -> None:
        self.assertTrue(is_serverless_repo("kb-entity-sync-serverless"))
        self.assertTrue(is_serverless_repo("fcsky-auth-server"))
        self.assertFalse(is_serverless_repo("fcsky-ui"))

    def test_rpm_lines_empty_fcsky_bt(self) -> None:
        from monthly_template import _rpm_lines

        self.assertEqual(_rpm_lines("", "", ""), ["FCSKY: ", "BT: "])

    def test_rpm_lines_with_versions(self) -> None:
        from monthly_template import _rpm_lines

        lines = _rpm_lines("17.1.1-4304", "17.1.1-4304", "")
        self.assertEqual(lines, ["FCSKY: FCSKY-17.1.1-4304", "BT: BaseThreadsFCSKY-17.1.1-4304"])

    def test_fjs_changes_with_lib_rpm(self) -> None:
        from monthly_template import build_monthly_description

        fields = _sample_monthly_fields(
            fjs_changes="yes",
            fjs_date="Jan/10, 2026",
            fjs_rpm="17.0.0-1155",
            fjs_lib_rpm="17.0.0.00-87",
            fjs_include_lib=True,
        )
        desc = build_monthly_description(
            fields,
            fcsky_rpm="",
            basethreads_rpm="",
            tomcat_rpm="",
            msa_lines=[],
            integration_lines=[],
            direct_sync_repos=(),
            serverless_repos=(),
            mysql_blocks=[],
            psql_blocks=[],
        )
        self.assertIn("FJS Changes: Yes, process on Jan/10, 2026", desc)
        self.assertNotIn("FJS Changes: yes\n", desc.lower())
        self.assertEqual(desc.lower().count("fjs changes:"), 1)
        self.assertIn(
            "Kindly upload the FJSSKY and fjssky-lib rpm to production from prod branch",
            desc,
        )
        self.assertIn("FJSSKY-LIB-17.0.0.00-87", desc)
        self.assertIn("FJSSky-17.0.0-1155", desc)

    def test_fjs_changes_with_lib_empty_rpm_prefixes(self) -> None:
        from monthly_template import build_monthly_description

        fields = _sample_monthly_fields(
            fjs_changes="yes",
            fjs_date="Jan/10, 2026",
            fjs_rpm="",
            fjs_lib_rpm="",
            fjs_include_lib=True,
        )
        desc = build_monthly_description(
            fields,
            fcsky_rpm="",
            basethreads_rpm="",
            tomcat_rpm="",
            msa_lines=[],
            integration_lines=[],
            direct_sync_repos=(),
            serverless_repos=(),
            mysql_blocks=[],
            psql_blocks=[],
        )
        block = (
            "Kindly upload the FJSSKY and fjssky-lib rpm to production from prod branch\n"
            "FJSSKY-LIB-\n"
            "FJSSky-"
        )
        self.assertIn(block, desc)

    def test_fjs_changes_without_lib(self) -> None:
        from monthly_template import build_monthly_description

        fields = _sample_monthly_fields(
            fjs_changes="yes",
            fjs_date="Jan/10, 2026",
            fjs_rpm="17.0.0-1155",
            fjs_include_lib=False,
        )
        desc = build_monthly_description(
            fields,
            fcsky_rpm="",
            basethreads_rpm="",
            tomcat_rpm="",
            msa_lines=[],
            integration_lines=[],
            direct_sync_repos=(),
            serverless_repos=(),
            mysql_blocks=[],
            psql_blocks=[],
        )
        self.assertIn(
            "Kindly upload the FJSSKY rpm to production from prod branch\nFJSSky-17.0.0-1155",
            desc,
        )
        self.assertNotIn("FJSSKY-LIB", desc)
        self.assertNotIn("fjssky-lib rpm", desc)

    def test_monthly_fjs_repos_omitted_from_msa_work(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Mar/11 - Mar/14, 2026",
            repo_lines=["fcsky-tenant-config", "fjssky:26.0.0-1253", "fjssky-lib"],
            monthly=_sample_monthly_fields(),
        )
        ticket = generate_ticket(data)
        self.assertIn("MSA Work:", ticket.description)
        self.assertIn("fcsky-tenant-config:", ticket.description)
        msa_section = ticket.description.split("MSA Work:")[1].split("Direct sync:")[0]
        self.assertNotIn("fjssky", msa_section)

    def test_monthly_rpm_section_without_versions(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_MONTHLY,
            date_display="Mar/11 - Mar/14, 2026",
            repo_lines=[],
            monthly=_sample_monthly_fields(),
        )
        ticket = generate_ticket(data)
        self.assertIn(
            "RPM upload branch details: prod branch from stage server to production server.",
            ticket.description,
        )
        self.assertIn("FCSKY: \nBT: ", ticket.description.replace("\r\n", "\n"))


class TestFormat(unittest.TestCase):
    def test_full_ticket_is_body_only(self) -> None:
        data = SREInput(
            sre_type=config.SRE_TYPE_URGENT,
            date_display="May/30, 2026",
            repo_lines=["fcsky"],
        )
        ticket = generate_ticket(data)
        full = format_full_ticket(ticket)
        self.assertEqual(full, ticket.description)
        self.assertNotIn("Upload patch to Production", full)


if __name__ == "__main__":
    unittest.main()
