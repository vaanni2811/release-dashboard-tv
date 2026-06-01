# Release Dashboard

A local Streamlit dashboard for FranConnect release workflows. It currently includes two tools:

- **SRE Generator** — draft SRE/Jira tickets from patch metadata
- **Hotfix Branch Automation** — create and track hotfix branches in Bitbucket

For details on each tool, read:

- [`SRE generator/PLAN.md`](SRE%20generator/PLAN.md)
- [`hotfix branch automation/PLAN.md`](hotfix%20branch%20automation/PLAN.md)

## Run

```bash
cd /home/vanni.chaudhary@ad.franconnect.com/release-dashboard
source .venv/bin/activate
streamlit run app.py
```
