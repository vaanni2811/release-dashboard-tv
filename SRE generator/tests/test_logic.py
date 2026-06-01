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
    normalize_repo_name,
    parse_repo_lines,
)


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


class TestClassification(unittest.TestCase):
    def test_fcsky_is_rpm_only(self) -> None:
        self.assertEqual(classify_repo("fcsky"), classify_repo("fcsky"))

    def test_direct_sync_known(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("fcsky-ui"), RepoBucket.DIRECT_SYNC)

    def test_serverless_suffix(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("foo-serverless"), RepoBucket.DIRECT_SYNC)

    def test_integration_prefix(self) -> None:
        from logic import RepoBucket

        self.assertEqual(classify_repo("integration-auth-service"), RepoBucket.INTEGRATION)

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
        self.assertEqual(ticket.description.count("Kindly execute below MYSQL queries on all Production tenants:"), 2)
        self.assertIn("Kindly execute below MYSQL queries ONLY on clientA:", ticket.description)
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
        self.assertIn("Kindly execute below MYSQL queries on all DEMO/MBE UAT tenants:", ticket.description)
        self.assertIn("Kindly execute below PSQL queries on all DEMO/MBE UAT tenants:", ticket.description)


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
