"""Structured FCSKY / MSA configuration UI for monthly release."""

from __future__ import annotations

import streamlit as st

import config
import monthly_config as mc


def _count_key(prefix: str) -> str:
    return f"mr_{prefix}_cfg_count"


def _init_count(prefix: str) -> int:
    key = _count_key(prefix)
    if key not in st.session_state:
        st.session_state[key] = 0
    return st.session_state[key]


def _render_fcsky_entry(index: int) -> mc.FcskyConfigEntry | None:
    st.markdown(f"**FCSKY change {index + 1}**")
    kind = st.selectbox(
        "Change type",
        options=list(mc.FCSKY_CONFIG_TYPES),
        key=f"mr_fcsky_kind_{index}",
    )
    if kind == mc.FCSKY_CONFIG_LANGUAGE:
        c1, c2 = st.columns(2)
        with c1:
            lang_name = st.text_input("Language name", key=f"mr_fcsky_lang_name_{index}", placeholder="Slovak")
        with c2:
            lang_abbr = st.text_input("Language abbreviation", key=f"mr_fcsky_lang_abbr_{index}", placeholder="sk")
        if not lang_name.strip() or not lang_abbr.strip():
            return None
        return mc.FcskyConfigEntry(kind=kind, lang_name=lang_name, lang_abbr=lang_abbr)
    return None


def _render_msa_entry(index: int) -> mc.MsaConfigEntry | None:
    st.markdown(f"**MSA change {index + 1}**")
    kind = st.selectbox(
        "Change type",
        options=list(mc.MSA_CONFIG_TYPES),
        key=f"mr_msa_kind_{index}",
    )

    if kind == mc.MSA_CONFIG_NEW_SERVICE:
        service = st.text_input("Service name", key=f"mr_msa_service_{index}", placeholder="document-viewer-service")
        ref = st.text_input("Ref SRE", key=f"mr_msa_ref_sre_{index}", placeholder="https://...")
        if not service.strip():
            return None
        return mc.MsaConfigEntry(kind=kind, service_name=service, ref_sre=ref)

    if kind == mc.MSA_CONFIG_NEW_SERVERLESS:
        name = st.text_input("Serverless name", key=f"mr_msa_serverless_{index}", placeholder="kb-entity-sync-serverless")
        ref = st.text_input("Refer SRE", key=f"mr_msa_ref_sre_{index}", placeholder="https://...")
        if not name.strip():
            return None
        return mc.MsaConfigEntry(kind=kind, serverless_name=name, ref_sre=ref)

    if kind == mc.MSA_CONFIG_BEDROCK_SQS:
        repo = st.text_input("Repo name", key=f"mr_msa_repo_{index}", placeholder="ai-integration-service")
        ref = st.text_input("Ref SRE", key=f"mr_msa_ref_sre_{index}", placeholder="https://...")
        if not repo.strip():
            return None
        return mc.MsaConfigEntry(kind=kind, repo_name=repo, ref_sre=ref)

    if kind == mc.MSA_CONFIG_FCSKY_MSA_YML:
        yml = st.text_input(
            "YML file names",
            key=f"mr_msa_yml_{index}",
            placeholder="application.yml and payment-service.yml",
        )
        ref = st.text_input("Ref Commit Id", key=f"mr_msa_ref_commit_{index}", placeholder="https://...")
        if not yml.strip():
            return None
        return mc.MsaConfigEntry(kind=kind, yml_files=yml, ref_commit_id=ref)

    if kind == mc.MSA_CONFIG_KAFKA_TOPIC:
        ref = st.text_input("Ref SRE", key=f"mr_msa_ref_sre_{index}", placeholder="https://...")
        return mc.MsaConfigEntry(kind=kind, ref_sre=ref)

    if kind == mc.MSA_CONFIG_ASM_GO_SHIFT:
        ref = st.text_input("Ref Ticket", key=f"mr_msa_ref_ticket_{index}", placeholder="https://...")
        return mc.MsaConfigEntry(kind=kind, ref_ticket=ref)

    if kind == mc.MSA_CONFIG_INTEGRATION_MSA_YML:
        yml = st.text_input(
            "YML file names",
            key=f"mr_msa_yml_{index}",
            placeholder="application.yml, integration-registry-service.yml",
        )
        ref = st.text_input("Ref Commit Id", key=f"mr_msa_ref_commit_{index}", placeholder="https://...")
        if not yml.strip():
            return None
        return mc.MsaConfigEntry(kind=kind, yml_files=yml, ref_commit_id=ref)

    if kind == mc.MSA_CONFIG_ASM_APP_YML:
        ref = st.text_input("Ref SRE", key=f"mr_msa_ref_sre_{index}", placeholder="https://...")
        return mc.MsaConfigEntry(kind=kind, ref_sre=ref)

    return None


def render_fcsky_config_section() -> tuple[str, str]:
    """Return (yes/NA, formatted details block)."""
    fcsky_cfg = st.selectbox(
        "FCSKY Configuration Changes",
        options=list(config.YES_NA_OPTIONS),
        key="mr_fcsky_cfg",
    )
    details = ""
    if fcsky_cfg == "yes":
        count = _init_count("fcsky")
        if count == 0:
            st.session_state[_count_key("fcsky")] = 1
            count = 1
        entries: list[mc.FcskyConfigEntry] = []
        for i in range(count):
            entry = _render_fcsky_entry(i)
            if entry:
                entries.append(entry)
        if st.button("+ Add FCSKY config change", key="mr_fcsky_cfg_add"):
            st.session_state[_count_key("fcsky")] = count + 1
            st.rerun()
        details = mc.format_fcsky_config_block(tuple(entries))
    return fcsky_cfg, details


def render_msa_config_section() -> tuple[str, str]:
    """Return (yes/NA, formatted details block)."""
    msa_cfg = st.selectbox(
        "MSA Configuration Changes",
        options=list(config.YES_NA_OPTIONS),
        key="mr_msa_cfg",
    )
    details = ""
    if msa_cfg == "yes":
        count = _init_count("msa")
        if count == 0:
            st.session_state[_count_key("msa")] = 1
            count = 1
        entries: list[mc.MsaConfigEntry] = []
        for i in range(count):
            entry = _render_msa_entry(i)
            if entry:
                entries.append(entry)
        if st.button("+ Add MSA config change", key="mr_msa_cfg_add"):
            st.session_state[_count_key("msa")] = count + 1
            st.rerun()
        details = mc.format_msa_config_block(tuple(entries))
    return msa_cfg, details
