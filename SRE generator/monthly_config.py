"""Structured FCSKY / MSA configuration change types for monthly release tickets."""

from __future__ import annotations

from dataclasses import dataclass

FCSKY_CONFIG_LANGUAGE = "Language addition"

FCSKY_CONFIG_TYPES: tuple[str, ...] = (FCSKY_CONFIG_LANGUAGE,)

MSA_CONFIG_NEW_SERVICE = "New Service"
MSA_CONFIG_NEW_SERVERLESS = "New serverless"
MSA_CONFIG_BEDROCK_SQS = "Bedrock, SQS permissions"
MSA_CONFIG_FCSKY_MSA_YML = "fcsky-msa-cloud-configuration (yml)"
MSA_CONFIG_KAFKA_TOPIC = "Kafka topic"
MSA_CONFIG_ASM_GO_SHIFT = "ASM variable (Go Shift Payment Gateway)"
MSA_CONFIG_INTEGRATION_MSA_YML = "integration-msa-cloud-configuration (yml)"
MSA_CONFIG_ASM_APP_YML = "ASM entries for application.yml"

MSA_CONFIG_TYPES: tuple[str, ...] = (
    MSA_CONFIG_NEW_SERVICE,
    MSA_CONFIG_NEW_SERVERLESS,
    MSA_CONFIG_BEDROCK_SQS,
    MSA_CONFIG_FCSKY_MSA_YML,
    MSA_CONFIG_KAFKA_TOPIC,
    MSA_CONFIG_ASM_GO_SHIFT,
    MSA_CONFIG_INTEGRATION_MSA_YML,
    MSA_CONFIG_ASM_APP_YML,
)


@dataclass(frozen=True)
class FcskyConfigEntry:
    kind: str
    lang_name: str = ""
    lang_abbr: str = ""


@dataclass(frozen=True)
class MsaConfigEntry:
    kind: str
    service_name: str = ""
    serverless_name: str = ""
    repo_name: str = ""
    yml_files: str = ""
    ref_sre: str = ""
    ref_commit_id: str = ""
    ref_ticket: str = ""


def format_fcsky_config_entry(entry: FcskyConfigEntry) -> str:
    if entry.kind == FCSKY_CONFIG_LANGUAGE:
        return (
            "Configuration changes : Add below language in FCSKY > app-config.properties "
            "(for new language addition):\n\n"
            f"i18n.lang.name={entry.lang_name.strip()}\n"
            f"i18n.lang.abbr={entry.lang_abbr.strip()}"
        )
    return ""


def format_msa_config_entry(entry: MsaConfigEntry) -> str:
    kind = entry.kind
    if kind == MSA_CONFIG_NEW_SERVICE:
        lines = [f"New Service : {entry.service_name.strip()}"]
        if entry.ref_sre.strip():
            lines.append(f"Ref SRE: {entry.ref_sre.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_NEW_SERVERLESS:
        name = entry.serverless_name.strip()
        lines = [f"New serverless: {name} : Lambda + SQS"]
        if entry.ref_sre.strip():
            lines.append(f"Refer SRE : {entry.ref_sre.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_BEDROCK_SQS:
        lines = [f"Bedrock,SQS permissions|{entry.repo_name.strip()}:"]
        if entry.ref_sre.strip():
            lines.append(f"Ref SRE: {entry.ref_sre.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_FCSKY_MSA_YML:
        yml = entry.yml_files.strip().replace(",", " and ")
        lines = [f"fcsky-msa-cloud-configuration > {yml}"]
        if entry.ref_commit_id.strip():
            lines.append(f"Ref Commit Id: {entry.ref_commit_id.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_KAFKA_TOPIC:
        lines = ["Kafka topic:"]
        if entry.ref_sre.strip():
            lines.append(f"Ref SRE : {entry.ref_sre.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_ASM_GO_SHIFT:
        lines = ["Add ASM variable for Go Shift Payment Gateway values"]
        if entry.ref_ticket.strip():
            lines.append(f"Ref Ticket: {entry.ref_ticket.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_INTEGRATION_MSA_YML:
        yml = entry.yml_files.strip()
        lines = [f"integration-msa-cloud-configuration> {yml}"]
        if entry.ref_commit_id.strip():
            lines.append(f"Ref Commit Id: {entry.ref_commit_id.strip()}")
        return "\n".join(lines)

    if kind == MSA_CONFIG_ASM_APP_YML:
        lines = ["ASM entries for application.yml:"]
        if entry.ref_sre.strip():
            lines.append(f"Ref SRE: {entry.ref_sre.strip()}")
        return "\n".join(lines)

    return ""


def format_fcsky_config_block(entries: tuple[FcskyConfigEntry, ...]) -> str:
    blocks = [format_fcsky_config_entry(e) for e in entries]
    return "\n\n".join(b for b in blocks if b.strip())


def format_msa_config_block(entries: tuple[MsaConfigEntry, ...]) -> str:
    blocks: list[str] = []
    for idx, entry in enumerate(entries, start=1):
        text = format_msa_config_entry(entry)
        if text.strip():
            blocks.append(f"{idx}. {text}" if len(entries) > 1 else text)
    return "\n\n".join(blocks)


BOOTSTRAP_DEFAULT_TEXT = (
    "Kindly do the unit-listing bootstrapping for all Production tenants "
    "as per production days processing"
)


def _repo_line_token(line: str) -> str:
    return line.split(":")[0].strip().lower()


def repos_include_fjs(repo_text: str) -> bool:
    """True when the repo list includes FJS / FJSSKY (e.g. shorthand line ``fjs``)."""
    for line in repo_text.splitlines():
        token = _repo_line_token(line)
        if token in ("fjs", "fjssky"):
            return True
    return False


def repos_include_fjssky_lib(repo_text: str) -> bool:
    """True when the repo list includes ``fjssky-lib``."""
    for line in repo_text.splitlines():
        if _repo_line_token(line) == "fjssky-lib":
            return True
    return False
