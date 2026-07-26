# VRS Roster Lab

An English-language Streamlit app for exploring Valve Regional Standings and testing
how Counter-Strike roster changes affect the inheritance of historical results.

## What it does

- Loads HLTV's daily live VRS Beta ranking and detailed point breakdown.
- Shows LAN wins, opponent network, bounty and head-to-head points by match and event.
- Applies Valve's public three-player roster-overlap rule to a simulated lineup.
- Separates live scores from an explicitly labelled indicative roster-change estimate.
- Uses Valve's official snapshot for historical-lineup enrichment and as a fallback.

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

## Data sources

- [HLTV Live VRS Beta](https://www.hltv.org/valve-ranking/teams) is the primary,
  frequently updated source. It may include matches and secured prize money from
  unfinished events.
- [Valve's official VRS repository](https://github.com/ValveSoftware/counter-strike_regional_standings)
  provides the official periodic snapshots and historical match lineups.

The simulated score is an inheritance estimate, not an official reranking. A roster
change can alter the global opponent network, top-ten selection and head-to-head
calculation for every team.
