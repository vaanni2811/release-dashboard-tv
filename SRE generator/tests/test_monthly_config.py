"""Tests for monthly configuration change formatting."""

from __future__ import annotations

import unittest

import monthly_config as mc


class TestMonthlyConfigFormat(unittest.TestCase):
    def test_fcsky_language(self) -> None:
        entry = mc.FcskyConfigEntry(kind=mc.FCSKY_CONFIG_LANGUAGE, lang_name="Slovak", lang_abbr="sk")
        text = mc.format_fcsky_config_entry(entry)
        self.assertIn("app-config.properties", text)
        self.assertIn("i18n.lang.name=Slovak", text)
        self.assertIn("i18n.lang.abbr=sk", text)

    def test_msa_new_service(self) -> None:
        entry = mc.MsaConfigEntry(
            kind=mc.MSA_CONFIG_NEW_SERVICE,
            service_name="document-viewer-service",
            ref_sre="https://jira/example",
        )
        text = mc.format_msa_config_entry(entry)
        self.assertIn("New Service : document-viewer-service", text)
        self.assertIn("Ref SRE: https://jira/example", text)

    def test_msa_new_serverless(self) -> None:
        entry = mc.MsaConfigEntry(
            kind=mc.MSA_CONFIG_NEW_SERVERLESS,
            serverless_name="kb-entity-sync-serverless",
            ref_sre="https://jira/sre",
        )
        text = mc.format_msa_config_entry(entry)
        self.assertIn("New serverless: kb-entity-sync-serverless : Lambda + SQS", text)
        self.assertIn("Refer SRE : https://jira/sre", text)

    def test_msa_multiple_numbered(self) -> None:
        entries = (
            mc.MsaConfigEntry(kind=mc.MSA_CONFIG_KAFKA_TOPIC, ref_sre="https://a"),
            mc.MsaConfigEntry(
                kind=mc.MSA_CONFIG_NEW_SERVICE,
                service_name="document-viewer-service",
                ref_sre="https://b",
            ),
        )
        block = mc.format_msa_config_block(entries)
        self.assertTrue(block.startswith("1."))
        self.assertIn("2. New Service", block)

    def test_repos_include_fjs_shorthand(self) -> None:
        self.assertTrue(mc.repos_include_fjs("fjs\nfcsky-ui"))

    def test_repos_include_fjs_fjssky(self) -> None:
        self.assertTrue(mc.repos_include_fjs("fjssky:26.0.0-1253"))

    def test_repos_exclude_fjs(self) -> None:
        self.assertFalse(mc.repos_include_fjs("fcsky-ui\nfcsky-msa"))

    def test_fjssky_lib_does_not_trigger_fjs_changes(self) -> None:
        self.assertFalse(mc.repos_include_fjs("fjssky-lib"))

    def test_repos_include_fjssky_lib(self) -> None:
        self.assertTrue(mc.repos_include_fjssky_lib("fjssky-lib:17.0.0.00-87"))
        self.assertFalse(mc.repos_include_fjssky_lib("fjssky"))


if __name__ == "__main__":
    unittest.main()
