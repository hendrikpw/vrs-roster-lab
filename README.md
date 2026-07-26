# VRS Roster Lab

An English-language Streamlit app for exploring Valve Regional Standings and testing
how Counter-Strike roster changes affect the inheritance of historical results.

## What it does

- Loads Valve's latest published global VRS snapshot.
- Shows the official starting value, head-to-head adjustment, ranking factors and
  contributing matches for every available team.
- Applies Valve's public three-player roster-overlap rule to a simulated lineup.
- Separates official scores from an explicitly labelled indicative reranking.
- Falls back to a bundled FaZe demo if Valve's repository is temporarily unavailable.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this directory to a GitHub repository.
2. In Streamlit Community Cloud, choose **Create app**.
3. Select the repository, branch and `app.py`.
4. Deploy. No secrets are required for the current version.

## Data note

Valve's published team detail files say that their event data is provided by HLTV.
The current public detail format does not expose an event name for every match, so
the MVP presents match and historical-core eligibility. A cached event-name
enrichment layer can be added without changing the simulator model.
