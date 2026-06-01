# Release Dashboard

A local Streamlit dashboard for FranConnect release workflows. It currently includes two tools:

- **SRE Generator** — draft SRE/Jira tickets from patch metadata
- **Hotfix Branch Automation** — create and track hotfix branches in Bitbucket

For details on each tool, read:

- [`SRE generator/PLAN.md`](SRE%20generator/PLAN.md)
- [`hotfix branch automation/PLAN.md`](hotfix%20branch%20automation/PLAN.md)

## Git (as of now)

Source code lives on **personal GitHub** while the tool is in pilot (you + one teammate):

| | |
| --- | --- |
| **Repository** | [github.com/vaanni2811/release-dashboard-tv](https://github.com/vaanni2811/release-dashboard-tv) |
| **Clone (HTTPS)** | `git clone https://github.com/vaanni2811/release-dashboard-tv.git` |
| **Clone (SSH)** | `git clone git@github.com:vaanni2811/release-dashboard-tv.git` |

**Do not commit:** `.env` (Bitbucket credentials). It is listed in `.gitignore`.

**Later (company approval):** mirror or move the repo to FranConnect **Bitbucket** like other team repos. App usage stays the same (clone → venv → local `.env` → run). Update the clone URL in this section when that happens.

### First-time setup (teammate)

1. Ask the repo owner to add your GitHub user under **Settings → Collaborators** on `release-dashboard-tv`.
2. Clone the repo (HTTPS or SSH above).
3. Follow [Run locally](#run-locally) and [Bitbucket credentials](#bitbucket-credentials-hotfix-tool-only) below.

### Push updates (repo owner / collaborator with write access)

```bash
cd release-dashboard-tv
git add -A
git status   # confirm .env is not listed
git commit -m "Your message"
git push origin main
```

**HTTPS auth:** GitHub does not accept account passwords for `git push`. Use username `vaanni2811` and a [Personal Access Token](https://github.com/settings/tokens) with **repo** scope as the password.

**SSH auth:** Add your SSH key to GitHub, set remote to `git@github.com:vaanni2811/release-dashboard-tv.git`, then `git push origin main`.

**If `git push` keeps failing** (invalid username/token), run the interactive helper in your terminal (you paste the PAT when prompted — it is not echoed):

```bash
cd release-dashboard-tv
bash scripts/push-github.sh
```

## Run locally

```bash
cd release-dashboard-tv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501). Select a tool in the sidebar.

If `python3 -m venv` fails on Ubuntu, install `python3.10-venv` or use `virtualenv .venv` instead.

## Bitbucket credentials (hotfix tool only)

SRE Generator does not need API access. Hotfix automation reads credentials from a local `.env` file (never committed).

```bash
cp .env.example .env
```

Edit `.env`:

```bash
BITBUCKET_EMAIL=you@company.com
BITBUCKET_API_TOKEN=your_atlassian_api_token
BITBUCKET_WORKSPACE=franconnect
```

Each person should use **their own** Atlassian API token. Create one under Atlassian account settings → Security → API tokens.

Optional: `BITBUCKET_TOKEN` (repository access token) instead of email + API token — see `.env.example`.
