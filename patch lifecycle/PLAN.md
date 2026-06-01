# Patch Lifecycle — plan and specification

This document defines the product intent, rules, and implementation map for **Patch Lifecycle** under `patch lifecycle/`.

## Problem statement

Hotfix and release patches are tracked manually in a Google Sheet after Jira assignment. The Jira patch list is temporary; after production deployment, patches may disappear from active Jira views while follow-up work remains:

- Merge/update release branch or prod branch
- Deploy to UAT
- Execute MySQL or PostgreSQL on Stage, then UAT
- Track configuration changes, QA verification, developer ownership
- Confirm final closure

Manual sheets lead to forgotten, delayed, or missed patches.

## Goal

A **database-backed** local Streamlit dashboard that:

1. Permanently stores every hotfix and release patch (manual entry in v1)
2. Tracks full lifecycle across Production, release/prod branch, Stage, UAT, DB queries, QA, and closure
3. Replaces the Google Sheet as the **system of record**
4. Surfaces pending follow-ups even when Jira no longer shows the patch

**Users:** FranConnect release / dev / QA operators (you + teammate in pilot; wider team when repo moves to Bitbucket).

**Independence:** Does not require Bitbucket or Jira in v1. Shared root dashboard only. Optional links to SRE tickets, PRs, deployments stored as URLs.

## Tool name (sidebar)

**Patch Lifecycle**

## Tech stack (MVP)

| Layer      | Choice |
| ---------- | ------ |
| Runtime    | Python 3.10+ |
| UI         | Streamlit (`ui.py` → `render()`) |
| Database   | SQLite 3 — local file, not in git |
| Data access| stdlib `sqlite3` (MVP); path via `config.py` |
| Logic      | Pure Python (`logic.py`) — lifecycle rules, validation, pending filters |
| Config     | `config.py` — patch types, status enums, defaults per type |
| Tests      | `tests/` — lifecycle rules, close validation, ID generation |

## Data sources (phased)

| Phase | Source |
| ----- | ------ |
| **v1 (MVP)** | Manual create/edit in dashboard |
| **v2** | Import from Google Sheet |
| **v2+** | Import/sync assigned patches from Jira |

## Patch types

| Type | Typical pattern | Notes |
| ---- | --------------- | ----- |
| Weekly Hotfix | Wednesday prod deploy | Then release/prod branch + UAT |
| Urgent Hotfix | Urgent / Saturday | Highlight until closed |
| Release Patch | End of release week | UAT + queries/config as needed |
| DB Query Patch | Queries on Stage then UAT | Stage before UAT query complete |
| Configuration Patch | Config changes | Track where applied |

## Lifecycle steps

Each step uses a status from:

`Not Required` | `Pending` | `In Progress` | `Completed` | `Blocked` | `Failed` | `Skipped` (with reason)

| Step | Field (conceptual) |
| ---- | ------------------ |
| Patch captured | Initial record created |
| Production deployed | Prod deploy done |
| Release branch updated | Merged/synced to release branch |
| Prod branch updated | Merged/synced to prod branch |
| Stage query executed | MySQL/PSQL on Stage |
| UAT query executed | MySQL/PSQL on UAT |
| UAT deployed | UAT deployment |
| QA verified | QA sign-off |
| Ready to close | All required steps done |
| Closed | Final state |

**Final status (listing):** see [Final status — computed + manual override](#final-status--computed--manual-override).

## Core patch fields (metadata)

- **Patch ID** — primary key shown in UI; format `FCSKY-122193` (Jira-style; entered manually in v1)
- **Bug ID** — optional linked bug; same format, e.g. `FCSKY-120767`
- Jira link — built from Patch ID or pasted URL
- Patch type, title, description
- Branch name
- Patch date, QA date, QA status, QA representative
- Developer name
- Common with / dependency info
- Product / module
- Release month / release name (e.g. `Release April 26`)
- Created by, created date, last updated by, last updated date

## Technical fields

- Repository names, service names (1:N via `patch_repositories`)
- RPM number, extra repositories, steps
- Configuration changes (text)
- MySQL queries, PostgreSQL queries (1:N via `patch_queries`)
- Query execution notes, build notes, deployment notes
- Links: SRE, PR, release-branch PR, UAT deployment, production deployment (`patch_links`)

## Business rules (enforced in `logic.py`)

1. Once captured, a patch is **never deleted** — only closed/archived.
2. When **Production deployed** = Completed → **Release branch updated** and **UAT deployed** default to **Pending** unless **Not Required**.
3. When patch has MySQL or PostgreSQL queries → **Stage query executed** = **Pending**.
4. **UAT query executed** cannot be **Completed** before **Stage query executed** is **Completed**.
5. **Cannot close** if any **required** lifecycle step is Pending, In Progress, Failed, or Blocked.
6. **Urgent** patches: UI highlight until **Closed**.
7. **Release** patches: remain prominent until UAT deploy + QA complete (TBD detail).
8. Every status change → `patch_activity_log`.
9. Skipped steps require a reason (text).
10. **All lifecycle statuses are editable manually** after patch creation (defaults are a starting point only).
11. **Patch type change:** never auto-overwrite existing statuses. UI must ask: *reset lifecycle to new type defaults* or *keep current values*.
12. When **Production deployed** becomes Completed, downstream rules (release branch, UAT, etc.) may still be updated manually; automated Pending promotion from rule 2 applies on status change events (implement in MVP or v1.1 — TBD in UI).

## Default lifecycle by patch type

Status key: **P** = Pending, **NR** = Not Required. Query columns use “if queries” = Pending only when the patch has MySQL/PostgreSQL rows.

### Weekly Hotfix

| Step | Default |
| ---- | ------- |
| Production deployed | P |
| Release branch updated | P |
| Prod branch updated | P |
| Stage query | P if queries, else NR |
| UAT query | P if queries, else NR |
| UAT deployed | P |
| QA verified | P |

### Urgent Hotfix

Same defaults as Weekly Hotfix. **`priority` = urgent**; UI **highlight until Closed**.

### Release Patch

| Step | Default |
| ---- | ------- |
| Production deployed | NR |
| Release branch updated | NR |
| Prod branch updated | NR |
| Stage query | P if queries, else NR |
| UAT query | P if queries, else NR |
| UAT deployed | P |
| QA verified | P |

### DB Query Patch

Ask on create (checkboxes):

| Question | If yes | If no |
| -------- | ------ | ----- |
| Linked to hotfix production deployment? | Production = P | Production = NR |
| Code/repo change exists? | Release branch + Prod branch = P | both NR |
| Query part of deployable patch? | UAT deployed = P | UAT deployed = NR |

Always: Stage query = P, UAT query = P, QA verified = P.

### Configuration Patch

Ask on create (checkboxes):

| Question | If yes | If no |
| -------- | ------ | ----- |
| Config applied in production? | Production = P | Production = NR |
| Config stored in repo? | Release branch = P | NR |
| Config stored in prod branch/repo? | Prod branch = P | NR |
| Must apply/test in UAT? | UAT deployed = P | UAT deployed = NR |

Always: Stage query = NR, UAT query = NR, QA verified = P.

Implemented in `config.py` + `logic.compute_initial_lifecycle()`.

## Final status — computed + manual override

**Decision:** **C — Both.**

| Column | Role |
| ------ | ---- |
| `system_status` | Computed from lifecycle; updated whenever lifecycle changes |
| `manual_status_override` | Optional; when set, drives **Final Status** in the UI |
| `current_status` | Deprecated alias — use `final_status` display from `resolve_patch_status_display()` |

**Computed (`system_status`) examples** (first open required step wins):

- Pending Production
- Pending Release Branch
- Pending Prod Branch
- Pending Stage Query
- Pending UAT Query
- Pending UAT Deployment
- Pending QA Verification
- Blocked (any lifecycle step Blocked or Failed)
- Ready to Close (all required steps done; not yet closed)
- Closed (closure completed)

**Manual override** (`manual_status_override`) — user-selected:

- On Hold
- Blocked by Dev
- Blocked by QA
- Waiting for Approval
- Duplicate
- Cancelled
- Not Going in Release

**UI display:**

| Override set? | Final Status column | Also show |
| ------------- | ------------------- | --------- |
| No | `system_status` | — |
| Yes | `manual_status_override` | **System Status** = `system_status` |

Logic: `logic.compute_system_status()`, `logic.resolve_patch_status_display()`.

## Operator identity (MVP)

**Decision:** **B** — fixed team dropdown in `config.OPERATORS`.

Pilot list:

- Vanni Chaudhary
- Tanisha Rawat

UI: operator selector in Patch Lifecycle sidebar (Streamlit `session_state` key `patch_lifecycle_operator`). The selected name is used for:

- `created_by` on new patches
- `updated_by` on edits
- `updated_by` on activity log entries

Add names by editing `config.py` until a central user service exists.

## Database schema (MVP)

**Path (MVP):** `patch lifecycle/data/patches.db` on each laptop. **Not committed to git.**  
**Later:** PostgreSQL on a shared server when the team outgrows per-machine SQLite.

### `patches`

| Column | Notes |
| ------ | ----- |
| id | PK, auto (internal SQLite row id) |
| patch_id | **Unique.** Business ID, e.g. `FCSKY-122193` (required on create) |
| bug_id | Optional, e.g. `FCSKY-120767` |
| jira_url | Optional override; default derived from patch_id if blank |
| title, description | |
| patch_type | Enum (see patch types above) |
| priority | `normal` / `urgent` (urgent for Urgent Hotfix) |
| branch_name | |
| db_linked_to_hotfix_prod | bool — DB Query create option |
| db_has_repo_change | bool — DB Query create option |
| db_query_part_of_deployable | bool — DB Query create option |
| config_applied_in_production | bool — Configuration create option |
| config_stored_in_repo | bool — Configuration create option |
| config_stored_in_prod_branch | bool — Configuration create option |
| config_must_apply_in_uat | bool — Configuration create option |
| release_name | e.g. `Release April 26` |
| patch_date, qa_date | DATE |
| qa_status, qa_rep | |
| developer_name, common_with | |
| product_module | |
| system_status | Computed from lifecycle (see above) |
| manual_status_override | Optional manual Final Status |
| is_archived | Boolean, default false |
| created_by, created_at, updated_by, updated_at | |

### `patch_repositories`

| Column | Notes |
| ------ | ----- |
| id, patch_id | FK |
| repo_name, service_name | |
| rpm_name, extra_repo | |
| build_notes, deployment_notes | |

### `patch_queries`

| Column | Notes |
| ------ | ----- |
| id, patch_id | FK |
| query_type | `mysql` / `postgresql` |
| query_text | |
| stage_status, stage_executed_by, stage_executed_at | |
| uat_status, uat_executed_by, uat_executed_at | |
| rollback_query, notes | |

### `patch_lifecycle_status`

One row per patch (1:1 in MVP).

| Column | Notes |
| ------ | ----- |
| patch_id | FK, unique |
| production_status | |
| release_branch_status | |
| prod_branch_status | |
| stage_query_status | |
| uat_query_status | |
| uat_deployment_status | |
| qa_verification_status | |
| closure_status | |
| blocker_reason | |

### `patch_links`

| Column | Notes |
| ------ | ----- |
| id, patch_id | FK |
| link_type | e.g. `jira`, `sre`, `pr`, `release_branch_pr`, `uat_deploy`, `prod_deploy` |
| url, label | |

### `patch_comments`

| Column | Notes |
| ------ | ----- |
| id, patch_id | FK |
| author, body, created_at | |

### `patch_activity_log`

| Column | Notes |
| ------ | ----- |
| id, patch_id | FK |
| action | e.g. `status_change`, `field_update`, `created` |
| field_name, old_value, new_value | |
| updated_by, updated_at | |

## UI views (MVP)

| View | Purpose |
| ---- | ------- |
| **Patch listing** | Sheet replacement — sortable/filterable table |
| **Pending follow-ups** | Patches with any required step not Completed / Not Required |
| **Patch detail** | Full record, edit, lifecycle updates, comments, activity |
| **Create patch** | Form — manual entry |

**Post-MVP views** (structure in PLAN, build after MVP stable):

- Weekly hotfix view (Wednesday / Saturday urgent / carry-forward)
- Release view (by `release_name`)

## MVP scope (v1)

1. Database init + schema migration script
2. Create patch manually
3. Patch listing with filters (type, developer, repo, status, release, pending bucket)
4. Patch detail + edit metadata
5. Repositories/services (multi-row)
6. MySQL/PostgreSQL queries (multi-row)
7. Lifecycle status editor + rule engine
8. Pending follow-ups view
9. Activity log on every change
10. Close validation (block invalid close)
11. Urgent patch highlighting in list

**Out of scope v1:** Sheet import, Jira import, Slack, Excel export, Jira/PR sync, multi-user auth.

## Google Sheet import (v2)

Source workbook: **FCSKY Production Upload** (and related tabs e.g. `FCSKY`, `UAT_Pending` — confirm per import).

### Sheet columns (pilot mapping)

| Sheet column | Maps to | Notes |
| ------------ | ------- | ----- |
| **Details** | `title`, `description`, Jira (`patch_id`, `bug_id`, `jira_url`) | Often multi-line: Jira keys (`FCSKY-…`), summary text, branch lines, file lists — parse or split on import |
| **Patch** | `branch_name`, `patch_repositories`, `patch_queries`, configuration text, steps | **Mixed cell** — branch, repos, extra repos, MySQL, PSQL, config, steps in one field; requires **parsing heuristics + manual review UI** |
| **QA Date** | `qa_date` | |
| **QA Status** | `qa_status` | e.g. `QA` |
| **Developer** | `developer_name` | Sheet uses short names (`vipin`, `vishal`, `prem`) — map via alias table in import config or manual fix |

**Not imported (by design):**

- QA Rep — not required
- Common With — not required

### Import behaviour (v2)

1. Row preview with parsed vs raw columns.
2. Flag rows that need manual review (unparsed Patch cell).
3. Operator confirms before insert (uses `config.OPERATORS` for `created_by`).
4. Lifecycle defaults applied via `compute_initial_lifecycle()` after type + flags are chosen.

## Version 2 (out of scope for v1)

- Google Sheet import (mapping above)
- Jira import / auto-refresh assigned patches
- Duplicate Jira detection
- Export Excel
- Slack reminders
- Jira status sync, Git PR sync
- SRE Generator integration (pre-fill from patch)

## Project layout (target)

| File / folder | Role |
| ------------- | ---- |
| `PLAN.md` | This specification |
| `config.py` | Enums, patch types, default lifecycle matrix |
| `db.py` | Connection, schema init |
| `models.py` | Schema / CRUD helpers |
| `logic.py` | Business rules, pending detection, close validation |
| `ui.py` | Streamlit entry `render()` — routing between views |
| `ui_list.py` | Listing + filters (optional split) |
| `ui_detail.py` | Detail + edit (optional split) |
| `ui_create.py` | Create form (optional split) |
| `tests/` | Unit tests for `logic.py` |

## Success criteria

- Google Sheet no longer required for new patches
- Patches remain visible after prod deploy / Jira disappearance
- Pending actions visible without manual sheet scanning
- Stage → UAT query order enforced
- Close blocked when follow-up incomplete
- Team trusts dashboard as source of truth

## Open decisions

Record answers here as product owner confirms:

| # | Topic | Answer |
| - | ----- | ------ |
| 1 | Database placement (local file path, shared path, server) | **A** — Local SQLite at `patch lifecycle/data/patches.db`; in `.gitignore`; PostgreSQL later |
| 2 | Patch ID format | **D** — User/Jira-style `FCSKY-<number>` as `patch_id` (unique); optional `bug_id` same pattern |
| 3 | Default lifecycle matrix per patch type | **Done** — see [Default lifecycle by patch type](#default-lifecycle-by-patch-type); editable after create; type change needs confirm |
| 4 | `current_status` — manual vs computed | **C** — `system_status` computed; optional `manual_status_override`; UI shows both when override set |
| 5 | User identity for created_by / activity (free text vs dropdown) | **B** — Dropdown from `config.OPERATORS` (pilot: Vanni Chaudhary, Tanisha Rawat); sidebar selection drives created/updated/activity |
| 6 | Google Sheet columns mapping (for v2) | **Done** — see [Google Sheet import (v2)](#google-sheet-import-v2) |

## Execution

```bash
cd /home/vanni.chaudhary@ad.franconnect.com/release-dashboard
source .venv/bin/activate
streamlit run app.py
```

Select **Patch Lifecycle** in the sidebar under **Release Overview/Tools**.

```bash
python -m unittest discover -s "patch lifecycle/tests" -t "patch lifecycle" -v
```

## Design principles

- Database = system of record; Jira = optional reference in v1
- Logic separate from UI — rules testable without Streamlit
- No patch deletes; audit everything material
- MVP is manual entry only; integrations are explicit later phases
