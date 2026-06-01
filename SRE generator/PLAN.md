# SRE Generator — plan and specification

This document defines the product intent, rules, and implementation map for the **SRE Generator** tool under `SRE generator/`.

## Problem statement

FranConnect patch and release deployments require SRE/Jira tickets with consistent wording, repo classification (RPM vs MSA vs direct sync), RPM lines, image tags, branch references, and optional SQL queries. Today these tickets are drafted manually from patch details — error-prone and repetitive.

## Goal

A **local** Streamlit tool that:

1. Collects patch metadata (type, dates, repos, RPMs, tags, queries)
2. Classifies repos and applies team shorthand/typo fixes
3. Outputs a **ready-to-paste** SRE/Jira ticket title and description
4. Requires **no external integrations** in v1 (no Jira, Bitbucket, Slack, etc.)

**Users:** FranConnect SRE / release team (local operators).

**Independence:** Does not depend on HP Branch Cut; shared only via root dashboard and `.env` (unused in v1).

## SRE types

| Type | Title pattern |
| ---- | ------------- |
| Weekly Production Patch | `Upload weekly patches to Production \| <DATE RANGE>` |
| Urgent Production Patch | `Upload patch to Production \| <DATE>` |
| DEMO/MBE UAT Patch | `Upload rpm from USTAGE to DEMO-UAT and MBE-UAT \| <DATE>` |

## Tech stack

| Layer   | Choice |
| ------- | ------ |
| Runtime | Python 3.10+ |
| UI      | Streamlit (`ui.py` → `render()`) |
| Logic   | Pure Python (`logic.py`) |
| Config  | `config.py` (shorthand, direct-sync list, defaults) |
| Tests   | `tests/test_logic.py` |

## Project layout

| File | Role |
| ---- | ---- |
| `ui.py` | Form inputs, generate button, copy-friendly output |
| `logic.py` | Repo parsing/classification, template assembly |
| `config.py` | SRE types, shorthand map, direct-sync repos, defaults |
| `tests/` | Unit tests (includes canonical user example) |
| `PLAN.md` | This specification |

## User inputs

### Common (all types)

- **SRE type** — weekly / urgent production / UAT
- **Date or date range** — free text (e.g. `May/27 - May/30, 2026`)
- **Repo list** — one per line or comma-separated; shorthand supported
- **Cache update required** — yes/no; defaults: **yes** (weekly, UAT), **no** (urgent)
- **Flush MSA cache** — yes/no; default **yes**

### Production (weekly + urgent)

- Hotfix branch (e.g. `hotfix_r26q2.15`)
- FCSKY RPM / BaseThreadsFCSKY RPM versions (optional)
- MSA & integration image tags (`repo:tag`, tag optional)
- MySQL queries + scope (all prod / specific tenant)
- PSQL queries + scope (all prod / specific tenant)

### UAT

- UAT branch (default `uat`)
- FCSKY / BaseThreadsFCSKY / tomcatFCSKY RPM (tomcat if applicable)
- MSA image tags
- Queries + scope (all DEMO/MBE UAT / specific tenant)

## Repo classification rules

1. **`fcsky`** → RPM section only (never direct sync). Missing RPM versions → `FCSKY-` and `BaseThreadsFCSKY-`.
2. **Direct sync:** `fcsky-ui`, `fcsky-static-resources`, `fcsky-internationalization`, any `*-serverless`, or explicitly marked `(direct sync)`.
3. **All other service repos** → MSA images (`repo:` or `repo:tag`).
4. **`integration-*` repos** → integration stage section (production templates).
5. **Dedupe** repos in output; preserve first-seen order.
6. **Shorthand / typo map** in `config.SHORTHAND_MAPPING` — e.g. `static`, `fcsky-static` → `fcsky-static-resources`; `ui`, `fcsky-ui` → `fcsky-ui`; `i18`, `fcsky-i18` → `fcsky-internationalization` (all direct sync).

## Output rules

- Omit empty sections completely.
- Do not invent RPM versions or image tags.
- MSA without tag → `repo-name:` (no placeholder text).
- Production templates use HP-APP / HP ECS / PROD wording; UAT uses USTAGE / DEMO-UAT / MBE-UAT.
- End with `Note:` (production) or `Notes:` (UAT): Kindly flush msa cache — unless flush disabled.

## Templates

See `logic.py` functions `_generate_weekly`, `_generate_urgent`, `_generate_uat` for exact wording.

### Example (weekly production)

**Input:** Weekly patch, May/27 - May/30, 2026, branch `hotfix_r26q2.15`, repos: fcsky, fcsky-commandcenter-service, unit-listing-service (×2), fcsky-static-resoucres, fcsky-cc, fcsky-ui.

**Output:** Title + description with RPM placeholders, MSA lines for commandcenter + unit-listing, direct sync for static-resources + ui, flush note.

## UI behavior

- Type-specific fields shown/hidden by SRE type.
- **Generate SRE ticket** validates date + repos; shows title and full copy-paste block.
- No API calls; no credentials required.

## Execution

```bash
cd /home/vanni.chaudhary@ad.franconnect.com/release-dashboard
source .venv/bin/activate
streamlit run app.py
```

Select **SRE Generator** in the sidebar.

```bash
python -m unittest discover -s "SRE generator/tests" -t "SRE generator" -v
```

## Future enhancements (out of scope)

- Jira/Confluence paste or API create
- Pre-fill from HP Branch Cut session
- Saved templates / history
- Repo picker from Bitbucket

## Design principles

- Logic separate from UI — all rules testable in `logic.py`
- Wording matches existing team templates exactly
- Preview-only v1 — operator copies into Jira manually


For execution:

cd /home/vanni.chaudhary@ad.franconnect.com/release-dashboard
source .venv/bin/activate
streamlit run app.py