# VRS Roster Lab

An English-language Streamlit app for exploring Valve Regional Standings and testing
how Counter-Strike roster changes affect the inheritance of historical results.

## What it does

- Loads HLTV's daily live VRS Beta ranking and detailed point breakdown.
- Shows LAN wins, opponent network, bounty and head-to-head points by match and event.
- Applies Valve's public three-player roster-overlap rule to a simulated lineup.
- Separates live scores from an explicitly labelled indicative roster-change estimate.
- Uses Valve's official snapshot for historical-lineup enrichment and as a fallback.
- Resolves newer event lineups from HLTV match pages instead of applying today's roster
  to historical results.
- Marks unresolved lineups as unknown and withholds the simulated score rather than
  reporting a false retained/lost result.
- Projects the currently listed contributions across Valve's six-month recency window
  under an explicit "no new results" assumption.
- Compares the same-roster decay curve with a simulated roster and identifies the
  least damaging modeled change window.
- Loads HLTV's upcoming VRS invite calendar and predicted event rankings, including
  the invite cutoff, point gap and regional invite track where available.
- Compares transfer candidates with current players across recent form, map ratings,
  opening duels, trading, side results and statistical playstyle indicators.
- Places the candidate's sporting profile beside the modeled VRS inheritance cost.
- Builds BO3 and BO5 veto suggestions from recent map results plus team-owned picks
  and bans, with smoothed map and series probabilities.

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
- [HLTV's VRS invite predictions](https://www.hltv.org/valve-ranking/invites)
  provide upcoming invite dates and predicted qualification lines.
- [Valve's official VRS repository](https://github.com/ValveSoftware/counter-strike_regional_standings)
  provides the official periodic snapshots and historical match lineups.
- [BO3.gg](https://bo3.gg/) provides the automated pro-player, map-result and veto
  statistics used by Transfer Lab and Map Veto. Its player rating is a separate
  10-point metric and is not HLTV Rating 3.0.

The simulated score is an inheritance estimate, not an official reranking. A roster
change can alter the global opponent network, top-ten selection and head-to-head
calculation for every team.
