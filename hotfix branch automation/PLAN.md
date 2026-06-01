# Hotfix branch automation — plan and specification

This document restates the product intent, rules, and implementation map for the local tool under `release-dashboard/hotfix branch automation/`.

## Problem statement

Weekly hotfix branches are created manually in Bitbucket; lineage is tracked in Excel. That implies:

- Manual choice of source: `prod`, a monthly release tag, or an existing hotfix branch  
- Manual lineage tracking  
- Special handling for monthly releases, release branches (e.g. `release_april26`), and optional freeze windows  
- Risk of error, inconsistency, and weak auditability

## Goal

A **local** automation tool with a **UI** that:

1. Lets the user pick a **repo** and a **hotfix week (Wednesday)**
2. Computes **branch name** and **source ref** automatically
3. **Creates** the branch in **Bitbucket Cloud** via API
4. Removes dependence on Excel for sequencing
5. Applies **release rules consistently**

## Tech stack


| Layer        | Choice                                                  |
| ------------ | ------------------------------------------------------- |
| Runtime      | Python 3.10+                                            |
| UI           | Streamlit (dropdown-first)                              |
| HTTP         | `requests`                                              |
| Dates        | `python-dateutil` (month arithmetic for Wednesday list) |
| External API | Bitbucket Cloud REST API 2.0                            |


## Authentication

- **Bitbucket repository access token** (or compatible bearer token) via environment variable only:  
`export BITBUCKET_TOKEN=xxxx`  
- **No token in code or committed files.**  
- Workspace: `BITBUCKET_WORKSPACE` or `config.BITBUCKET_WORKSPACE`.

## Project layout


| File               | Role                                                           |
| ------------------ | -------------------------------------------------------------- |
| `app.py`           | Streamlit UI, cache-backed Bitbucket load, create action       |
| `bitbucket.py`     | List branches, resolve branch/tag → commit hash, create branch |
| `logic.py`         | Pure decision engine (freeze, sequencing, source selection)    |
| `utils.py`         | Quarter/prefix, Wednesday list, release branch name from date  |
| `config.py`        | Workspace default, `REPOS` dropdown, `PROD_BRANCH`             |
| `requirements.txt` | Dependencies                                                   |
| `PLAN.md`          | This specification                                             |


## User inputs (UI)

- **Repo** — dropdown from `config.REPOS`  
- **Hotfix date** — Wednesday dropdown (current month + next month)

## Admin inputs (monthly)

- **Release live date** (e.g. `2026-04-08`)  
- **Release tag** (e.g. `prod_tag_17mar26`)  
- **Release branch** — optional override; default derived from release live date: `release_<month><yy>` in lowercase full month name, e.g. `release_april26`

## Optional inputs

- **Freeze window**: start date and end date (both required if either is set)  
- If hotfix Wednesday falls **inside** the freeze window → **block** creation

## Business logic

### 1. Branch naming

- Pattern: `hotfix_rYYqQ.N`  
- **YY** — two-digit year from the **hotfix date**  
- **Q** — calendar quarter: Q1 Jan–Mar, Q2 Apr–Jun, Q3 Jul–Sep, Q4 Oct–Dec  
- **N** — integer sequence **per repo, per quarter prefix** (`hotfix_rYYqQ`), determined from **Bitbucket branch list**

### 2. Hotfix flow (decision engine)

1. **Freeze** — if hotfix date ∈ [freeze_start, freeze_end] → block.
2. **Existing hotfix branches** — filter remote branches matching `hotfix_rYYqQ.*` for the hotfix date’s prefix; if any exist, take **max N**, next branch is `.N+1`, **source = branch** `hotfix_rYYqQ.<max N>`.
3. **First hotfix of the quarter** (no matching `hotfix_rYYqQ.*`):
  - If **release branch** exists on the repo (name = derived or overridden `release_*`) → **source = release tag** (admin). If tag is empty → **block** with a clear message.  
  - Else → **source = `prod`** (configurable `PROD_BRANCH`).
4. **Create** — `POST /2.0/repositories/{workspace}/{repo_slug}/refs/branches` with `name` and `target.hash` resolved from the chosen branch or tag.

### Decision table


| Scenario                             | Source                                  |
| ------------------------------------ | --------------------------------------- |
| Existing `hotfix_rYYqQ.*`            | Latest hotfix **branch** (highest `.N`) |
| First hotfix + release branch exists | **Release tag**                         |
| First hotfix + no release branch     | `**prod`**                              |


## Bitbucket as source of truth

- **Branches and tags** — fetched from Bitbucket; sequencing uses **actual** branch names.  
- **Release rules** (live date, tag, freeze) — **UI / config** until a future config service exists.

## UI behavior (`app.py`)

- Metrics / text: **proposed branch**, **source ref**, **type** (branch vs tag), **reason**  
- **Refresh preview from Bitbucket** — clears short TTL cache and reloads branches + release-branch existence  
- **Create branch** — disabled without token, workspace, and valid repo slug; resolves hash and posts create API  
- Without `BITBUCKET_TOKEN`, UI still shows **naming and rules** with an **empty** branch list (hypothetical “first hotfix” path)

## Execution

```bash
cd release-dashboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BITBUCKET_TOKEN=   # set when you have a token
export BITBUCKET_WORKSPACE=your-workspace
streamlit run app.py
```

## Future enhancements (out of scope for v1)

- Multi-repo batch operations  
- Slack notifications  
- Audit logs (who created what)  
- Stronger freeze enforcement / roles  
- Auto-detect release tags  
- Jenkins / pipeline integration  
- Central config service for release metadata

## Design principles

- Bitbucket = truth for **refs**  
- Config/UI = truth for **release policy** until automated further  
- Per-repo sequencing (simple, scales with `config.REPOS`)  
- UI-first for non-developer operators  
- No Excel dependency for lineage



For execution:

cd /home/vanni.chaudhary@ad.franconnect.com/release-dashboard
source .venv/bin/activate
streamlit run app.py
