from __future__ import annotations

import html
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from vrs_data import (
    DATA_MODEL_VERSION,
    VRSDataError,
    build_vrs_timeline,
    fallback_data,
    load_hltv_invite_ranking,
    load_hltv_invites,
    load_hltv_live_standings,
    load_hltv_team_detail,
    load_latest_standings,
    load_team_detail,
    project_vrs,
    simulate_roster,
)


st.set_page_config(
    page_title="VRS Roster Lab",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Oswald:wght@500;600;700&display=swap');
    :root {
        --paper: #f3f0e8;
        --ink: #151515;
        --muted: #6d685e;
        --line: #cfc8b8;
        --red: #e23a32;
        --green: #2e7d5b;
        --amber: #d89b2b;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container { max-width: 1500px; padding: 1.15rem 2rem 3rem; }
    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: "Oswald", sans-serif !important;
        letter-spacing: -0.025em;
    }
    p, label, button, input, [data-testid="stMarkdownContainer"] {
        font-family: "Inter", sans-serif;
    }
    header[data-testid="stHeader"] { background: rgba(243, 240, 232, .85); }
    .vrs-nav {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid var(--ink); padding: 0 0 14px; margin-bottom: 18px;
    }
    .brand { display: flex; align-items: center; gap: 13px; }
    .brand-mark {
        width: 46px; height: 38px; background: var(--red);
        clip-path: polygon(0 0, 66% 0, 100% 50%, 66% 100%, 0 100%, 34% 50%);
    }
    .brand-name { font: 700 28px/1 "Oswald", sans-serif; text-transform: uppercase; }
    .source-note { color: var(--muted); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
    .team-hero { padding: 20px 0 12px; position: relative; }
    .eyebrow { color: var(--red); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .12em; }
    .team-line { display: flex; align-items: end; gap: 14px; margin: 3px 0 4px; }
    .team-badge {
        width: 66px; height: 66px; border: 1px solid var(--ink);
        display: grid; place-items: center; color: var(--red);
        font: 700 28px/1 "Oswald", sans-serif;
    }
    .team-name { font: 700 58px/.98 "Oswald", sans-serif; }
    .rank-line { color: var(--muted); font-size: 16px; }
    .score-row { display: flex; align-items: baseline; gap: 12px; margin-top: 14px; }
    .score { font: 700 70px/.9 "Oswald", sans-serif; letter-spacing: -.04em; }
    .score-label { font: 600 25px/1 "Oswald", sans-serif; text-transform: uppercase; }
    .roster-strip { display: flex; flex-wrap: wrap; gap: 9px; margin: 18px 0 17px; }
    .player-chip {
        border: 1px solid var(--line); padding: 10px 16px;
        font: 600 15px/1 "Inter", sans-serif; background: rgba(255,255,255,.17);
    }
    .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--line); margin: 12px 0 24px; }
    .metric-box { padding: 15px 18px; border-right: 1px solid var(--line); }
    .metric-box:last-child { border-right: 0; }
    .metric-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .09em; }
    .metric-value { font: 600 31px/1.1 "Oswald", sans-serif; margin-top: 5px; }
    .green { color: var(--green); } .amber { color: var(--amber); } .red { color: var(--red); }
    .sim-panel {
        border-left: 1px solid var(--line); padding: 16px 0 10px 26px; min-height: 680px;
    }
    .sim-panel h2 { font-size: 34px; margin: 0 0 4px; }
    .panel-copy { color: var(--muted); font-size: 14px; margin-bottom: 16px; }
    .impact {
        margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--line);
    }
    .impact-number { font: 700 58px/.95 "Oswald", sans-serif; color: var(--red); }
    .impact-label { color: var(--muted); font-size: 13px; margin-top: 4px; }
    .formula { font: 600 27px/1.1 "Oswald", sans-serif; margin-top: 13px; }
    .disclaimer {
        border-left: 3px solid var(--amber); padding: 9px 12px; margin-top: 14px;
        color: var(--muted); background: rgba(216,155,43,.07); font-size: 12px;
    }
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stTextInput"] > div > div > input {
        border-radius: 0 !important; background: rgba(255,255,255,.22) !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { font-family: "Inter"; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--red) !important; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    div[data-testid="stAlert"] { border-radius: 0; }
    @media (max-width: 900px) {
        .block-container { padding: 1rem; }
        .team-name { font-size: 42px; }
        .score { font-size: 54px; }
        .metric-grid { grid-template-columns: 1fr; }
        .metric-box { border-right: 0; border-bottom: 1px solid var(--line); }
        .sim-panel { border-left: 0; border-top: 1px solid var(--line); padding: 22px 0 0; min-height: auto; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def get_standings():
    return load_hltv_live_standings()


@st.cache_data(ttl=3600, show_spinner=False)
def get_official_standings():
    return load_latest_standings()


@st.cache_data(ttl=3600, show_spinner=False)
def get_official_detail(url: str):
    return load_team_detail(url)


@st.cache_data(ttl=900, show_spinner=False)
def get_live_detail(
    team_row: dict,
    official_detail: dict | None,
    data_model_version: str,
):
    # The explicit version argument invalidates Streamlit's cache when roster
    # attribution changes inside the imported data module.
    return load_hltv_team_detail(team_row, official_detail)


@st.cache_data(ttl=3600, show_spinner=False)
def get_invites(data_model_version: str):
    return load_hltv_invites()


@st.cache_data(ttl=3600, show_spinner=False)
def get_invite_ranking(event: dict, data_model_version: str):
    return load_hltv_invite_ranking(event)


fallback_snapshot, fallback_standings, fallback_detail = fallback_data()
using_fallback = False
try:
    snapshot, standings = get_standings()
except VRSDataError:
    try:
        snapshot, standings = get_official_standings()
        snapshot["source"] = "Valve official snapshot"
    except VRSDataError:
        snapshot, standings = fallback_snapshot, fallback_standings
        using_fallback = True


st.markdown(
    f"""
    <div class="vrs-nav">
      <div class="brand"><div class="brand-mark"></div><div class="brand-name">VRS Roster Lab</div></div>
      <div class="source-note">{html.escape(snapshot.get('source', 'Valve official snapshot'))} · {snapshot['date'].replace('_', '-')}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

team_names = [row["team"] for row in standings]
default_index = team_names.index("FaZe") if "FaZe" in team_names else 0
selected_name = st.selectbox(
    "Select a ranked team",
    team_names,
    index=default_index,
    help="Teams from HLTV's current live VRS calculation.",
)
selected = next(row for row in standings if row["team"] == selected_name)

try:
    if selected.get("source") == "HLTV Live VRS (Beta)":
        official_detail = None
        try:
            _, official_rows = get_official_standings()
            official_row = next(
                (row for row in official_rows if row["team"].casefold() == selected_name.casefold()),
                None,
            )
            if official_row and official_row["detail_url"]:
                official_detail = get_official_detail(official_row["detail_url"])
        except VRSDataError:
            pass
        detail = get_live_detail(selected, official_detail, DATA_MODEL_VERSION)
    else:
        detail = (
            fallback_detail
            if using_fallback or not selected["detail_url"]
            else get_official_detail(selected["detail_url"])
        )
except VRSDataError:
    detail = fallback_detail
    using_fallback = True

if using_fallback:
    st.warning("Live HLTV and official Valve data are temporarily unavailable. Showing the bundled FaZe demo.")

analysis_tab, timeline_tab, invite_tab, rankings_tab, method_tab = st.tabs(
    [
        "TEAM ANALYSIS",
        "VRS TIMELINE",
        "INVITE RACE",
        "GLOBAL RANKINGS",
        "METHODOLOGY",
    ]
)

with analysis_tab:
    left, right = st.columns([2.1, 0.9], gap="large")

    with right:
        st.markdown(
            """
            <div class="sim-panel">
              <h2>Simulate roster changes</h2>
              <div class="panel-copy">Select players who leave the current five-player roster.</div>
            """,
            unsafe_allow_html=True,
        )
        leaving = st.multiselect(
            "Players leaving",
            detail["roster"],
            placeholder="Choose up to five players",
        )
        replacements_text = st.text_input(
            "Replacement players",
            placeholder="e.g. siuhy, lauNX",
            help="Optional. Re-signing a historical player can restore overlap with an older core.",
        )
        replacements = [name.strip() for name in replacements_text.split(",") if name.strip()]
        simulation = simulate_roster(detail, leaving, replacements)

        delta = simulation["indicative_delta"]
        delta_text = f"{delta:+,.0f}" if delta is not None else "N/A"
        score_text = (
            f"{simulation['indicative_score']:,.0f}"
            if simulation["indicative_score"] is not None
            else "N/A"
        )
        unknown_text = (
            f" · {simulation['unknown_matches']} lineups unknown"
            if simulation["unknown_matches"]
            else ""
        )
        st.markdown(
            f"""
              <div class="impact">
                <div class="impact-number">{delta_text}</div>
                <div class="impact-label">indicative VRS change</div>
                <div class="formula">{detail['final_score']:,.0f} → {score_text}</div>
                <div class="impact-label">{simulation['lost_matches']} matches lost · {simulation['fragile_matches']} at the 3/5 threshold{unknown_text}</div>
              </div>
              <div class="disclaimer">
                This is an inheritance estimate, not an official reranking. Exact VRS requires Valve's
                full global network, top-ten selection and normalization to be recalculated.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(
            "Why can the score increase?",
            expanded=delta is not None and delta > 0,
        ):
            st.markdown(
                """
                A roster change does **not** award new VRS points. The estimate removes historical
                results that no longer share at least three players with the simulated roster.
                If the removed history contains negative head-to-head adjustments, losing those
                penalties can outweigh positive points that are lost at the same time.
                """
            )
            breakdown = pd.DataFrame(simulation["component_breakdown"])
            if not breakdown.empty:
                breakdown_display = breakdown.rename(
                    columns={
                        "component": "Component",
                        "current": "Current",
                        "simulated": "Simulated",
                        "change": "Change",
                    }
                )
                st.dataframe(
                    breakdown_display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Current": st.column_config.NumberColumn(format="%.0f"),
                        "Simulated": st.column_config.NumberColumn(format="%.0f"),
                        "Change": st.column_config.NumberColumn(format="%+.0f"),
                    },
                )
            st.caption(
                "This is an inheritance explanation, not a guaranteed official gain. Valve "
                "recalculates the full global opponent and head-to-head network."
            )

    with left:
        initials = "".join(part[0] for part in detail["team"].split()[:2]).upper()
        roster_html = "".join(
            f'<div class="player-chip">{html.escape(player)}</div>' for player in detail["roster"]
        )
        factor_ratio = simulation["factor_ratio"]
        factor_ratio_text = f"{factor_ratio:.0%}" if factor_ratio is not None else "N/A"
        factor_ratio_class = (
            "green"
            if factor_ratio is not None and factor_ratio >= .8
            else "amber"
            if factor_ratio is None or factor_ratio >= .5
            else "red"
        )
        st.markdown(
            f"""
            <div class="team-hero">
              <div class="eyebrow">Current live VRS roster</div>
              <div class="team-line">
                <div class="team-badge">{html.escape(initials)}</div>
                <div>
                  <div class="team-name">{html.escape(detail['team'])}</div>
                  <div class="rank-line">#{detail['global_rank']} worldwide · #{detail['regional_rank']} {html.escape(detail['region'])}</div>
                </div>
              </div>
              <div class="score-row"><div class="score">{detail['final_score']:,.0f}</div><div class="score-label">VRS points</div></div>
              <div class="roster-strip">{roster_html}</div>
              <div class="metric-grid">
                <div class="metric-box"><div class="metric-label">Starting rank value</div><div class="metric-value">{detail['starting_score']:,.1f}</div></div>
                <div class="metric-box"><div class="metric-label">Head-to-head adjustment</div><div class="metric-value {'green' if detail['h2h_total'] >= 0 else 'red'}">{detail['h2h_total']:+,.1f}</div></div>
                <div class="metric-box"><div class="metric-label">Retained factor support</div><div class="metric-value {factor_ratio_class}">{factor_ratio_text}</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if simulation["event_groups"]:
            st.subheader("VRS points by event")
            st.caption(
                "Points shown are the sum of HLTV's listed LAN, opponent-network, bounty and "
                "head-to-head rows. The 400-point base is not assigned to an event."
            )
            events = pd.DataFrame(simulation["event_groups"])
            event_display = events[
                [
                    "event",
                    "current_points",
                    "retained_points",
                    "lost_points",
                    "unknown_points",
                    "status",
                ]
            ].rename(
                columns={
                    "event": "Event",
                    "current_points": "Current points",
                    "retained_points": "Retained",
                    "lost_points": "Lost",
                    "unknown_points": "Unverified",
                    "status": "Status",
                }
            )
            st.dataframe(
                event_display,
                width="stretch",
                hide_index=True,
                column_config={
                    "Current points": st.column_config.NumberColumn(format="%.0f"),
                    "Retained": st.column_config.NumberColumn(format="%.0f"),
                    "Lost": st.column_config.NumberColumn(format="%.0f"),
                    "Unverified": st.column_config.NumberColumn(format="%.0f"),
                },
            )

        st.subheader("Live match influence and roster eligibility")
        st.caption(
            "HLTV's live VRS detail includes matches from the current day. Valve groups historical "
            "results into the same ranked entity when at least three players overlap. "
            "Rows marked “At risk” sit exactly on that threshold."
        )
        match_rows = pd.DataFrame(simulation["rows"])
        if not match_rows.empty:
            match_rows["Core"] = match_rows.apply(
                lambda row: (
                    " · ".join(row["roster"])
                    if row.get("roster_verified", bool(row["roster"]))
                    else "Unverified historical lineup"
                ),
                axis=1,
            )
            match_rows["Core overlap"] = match_rows["overlap"].apply(
                lambda value: f"{int(value)} / 5" if pd.notna(value) else "Unknown"
            )
            match_rows["Lineup source"] = match_rows.apply(
                lambda row: row.get("roster_source", "Bundled / official"),
                axis=1,
            )
            match_rows["H2H"] = match_rows["h2h"].map(lambda value: f"{value:+.2f}")
            match_rows["Factor support"] = (
                match_rows["bounty_adjusted"]
                + match_rows["network_adjusted"]
                + match_rows["lan_adjusted"]
            ).map(lambda value: f"{value:.3f}")
            display = match_rows[
                [
                    "date",
                    "opponent",
                    "event",
                    "result",
                    "Core",
                    "Core overlap",
                    "Lineup source",
                    "H2H",
                    "status",
                ]
            ].rename(
                columns={
                    "date": "Date",
                    "opponent": "Opponent",
                    "event": "Event",
                    "result": "W/L",
                    "status": "Status",
                }
            )
            st.dataframe(
                display,
                width="stretch",
                hide_index=True,
                height=430,
            )
        else:
            st.info("No contributing matches were listed for this roster.")

        with st.expander("Historical roster cores"):
            cores = pd.DataFrame(simulation["core_groups"])
            if not cores.empty:
                st.dataframe(
                    cores[["roster", "matches", "overlap", "status"]].rename(
                        columns={
                            "roster": "Historical core",
                            "matches": "Matches",
                            "overlap": "Current overlap",
                            "status": "Status",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )

        if detail["prizes"]:
            with st.expander("Prize-money support used by the VRS model"):
                prizes = pd.DataFrame(detail["prizes"]).rename(
                    columns={
                        "date": "Event end date",
                        "age_weight": "Age weight",
                        "prize": "Prize winnings",
                        "scaled_prize": "Age-adjusted winnings",
                    }
                )
                st.dataframe(
                    prizes,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Prize winnings": st.column_config.NumberColumn(format="$%,.0f"),
                        "Age-adjusted winnings": st.column_config.NumberColumn(format="$%,.0f"),
                    },
                )
                st.caption(
                    "Valve's published detail file exposes event dates and winnings, but not the event names. "
                    "HLTV event-name enrichment is the next data layer."
                )

with timeline_tab:
    st.subheader(f"VRS timeline · {detail['team']}")
    st.caption(
        "Project the currently listed VRS contributions forward with no new results, "
        "then compare that baseline with a simulated roster."
    )
    if not detail.get("contributions"):
        st.info(
            "Timeline projections require HLTV's live contribution rows and are unavailable "
            "while the app is using an official or bundled fallback snapshot."
        )
    else:
        snapshot_day = datetime.strptime(
            detail["snapshot_date"].replace("_", "-"), "%Y-%m-%d"
        ).date()
        controls, summary = st.columns([0.9, 1.6], gap="large")
        with controls:
            target_date = st.date_input(
                "Projection date",
                value=snapshot_day + timedelta(days=30),
                min_value=snapshot_day,
                max_value=snapshot_day + timedelta(days=183),
                help="The model can project until all currently listed results have aged out.",
            )
            timeline_leaving = st.multiselect(
                "Players leaving",
                detail["roster"],
                key="timeline_players_leaving",
            )
            timeline_replacements_text = st.text_input(
                "Replacement players",
                placeholder="e.g. siuhy, lauNX",
                key="timeline_replacements",
            )
            timeline_replacements = [
                name.strip()
                for name in timeline_replacements_text.split(",")
                if name.strip()
            ]
            projection = project_vrs(
                detail,
                target_date,
                timeline_leaving,
                timeline_replacements,
            )
        with summary:
            metric_columns = st.columns(4)
            metric_columns[0].metric("Current VRS", f"{detail['final_score']:,.0f}")
            metric_columns[1].metric(
                "No-new-results baseline",
                f"{projection['baseline_score']:,.0f}",
                f"{projection['decay_delta']:+,.0f}",
            )
            metric_columns[2].metric(
                "Simulated roster",
                (
                    f"{projection['projected_score']:,.0f}"
                    if projection["projected_score"] is not None
                    else "N/A"
                ),
            )
            metric_columns[3].metric(
                "Roster-only impact",
                (
                    f"{projection['roster_delta']:+,.0f}"
                    if projection["roster_delta"] is not None
                    else "N/A"
                ),
            )
            if not projection["projection_complete"]:
                st.warning(
                    f"{projection['unknown_rows']} historical contribution rows have no verified "
                    "lineup, so the changed-roster projection is intentionally withheld."
                )

        timeline = build_vrs_timeline(
            detail,
            timeline_leaving,
            timeline_replacements,
        )
        chart_rows = pd.DataFrame(timeline["rows"])
        chart_rows["Date"] = pd.to_datetime(chart_rows["date"])
        chart_rows = chart_rows.set_index("Date")[
            ["baseline_score", "projected_score"]
        ].rename(
            columns={
                "baseline_score": "Same roster",
                "projected_score": "Simulated roster",
            }
        )
        st.line_chart(chart_rows, color=["#6d685e", "#e23a32"])

        best_window = timeline["best_window"]
        if (timeline_leaving or timeline_replacements) and best_window:
            st.markdown(
                f"**Least damaging modeled change window:** "
                f"{best_window['date']} · roster-only impact "
                f"{best_window['roster_delta']:+,.0f} points."
            )

        event_rows = pd.DataFrame(projection["event_groups"])
        if not event_rows.empty:
            event_display = event_rows[
                [
                    "event",
                    "current_points",
                    "baseline_points",
                    "simulated_points",
                    "roster_delta",
                    "status",
                ]
            ].rename(
                columns={
                    "event": "Event",
                    "current_points": "Current",
                    "baseline_points": "At target date",
                    "simulated_points": "With roster",
                    "roster_delta": "Roster impact",
                    "status": "Status",
                }
            )
            st.dataframe(
                event_display,
                width="stretch",
                hide_index=True,
                column_config={
                    "Current": st.column_config.NumberColumn(format="%.0f"),
                    "At target date": st.column_config.NumberColumn(format="%.0f"),
                    "With roster": st.column_config.NumberColumn(format="%.0f"),
                    "Roster impact": st.column_config.NumberColumn(format="%+.0f"),
                },
            )
        st.markdown(
            """
            <div class="disclaimer">
              Timeline assumption: the team plays no new matches. Existing results keep full
              recency weight for 30 days and then decay linearly to zero by day 183. This is an
              explanatory projection, not an official future score: Valve will recalculate the
              global opponent network, top-ten selections, bounties and head-to-head values.
            </div>
            """,
            unsafe_allow_html=True,
        )

with invite_tab:
    st.subheader("Tournament invite race")
    st.caption(
        "Explore HLTV's predicted VRS ranking at upcoming tournament invite dates. "
        "The qualification line is event- and region-specific."
    )
    try:
        invite_events = get_invites(DATA_MODEL_VERSION)
    except VRSDataError as exc:
        invite_events = []
        st.warning(f"HLTV's invite calendar is temporarily unavailable: {exc}")

    if invite_events:
        chosen_event = st.selectbox(
            "Upcoming event",
            invite_events,
            format_func=lambda event: (
                f"{event['name']} · invite date {event['invite_date']}"
            ),
        )
        try:
            invite_ranking = get_invite_ranking(chosen_event, DATA_MODEL_VERSION)
        except VRSDataError as exc:
            invite_ranking = None
            st.warning(f"This invite prediction is temporarily unavailable: {exc}")

        if invite_ranking:
            available_tracks = list(invite_ranking["tracks"])
            selected_track = st.selectbox(
                "Invite track",
                available_tracks,
                index=(
                    available_tracks.index("Global")
                    if "Global" in available_tracks
                    else 0
                ),
                help="Some tournaments allocate separate Global, Europe, Americas or Asia slots.",
            )
            track_data = invite_ranking["tracks"][selected_track]
            track_rows = track_data["rows"]
            cutoff = track_data["cutoff"]
            first_out = track_data["first_out"]
            selected_invite_team = next(
                (
                    row
                    for row in track_rows
                    if row["team"].casefold() == selected_name.casefold()
                ),
                None,
            )

            invite_metrics = st.columns(4)
            invite_metrics[0].metric("Invite date", invite_ranking["ranking_date"])
            invite_metrics[1].metric(
                f"{selected_track} slots",
                sum(row["qualified"] for row in track_rows),
            )
            invite_metrics[2].metric(
                f"{selected_name} position",
                (
                    f"#{selected_invite_team['rank']}"
                    if selected_invite_team
                    else "Not listed"
                ),
            )
            team_status = selected_invite_team["status"] if selected_invite_team else "Not listed"
            invite_metrics[3].metric(f"{selected_name} status", team_status)

            if selected_invite_team and cutoff:
                if selected_invite_team["qualified"]:
                    comparison = first_out["points"] if first_out else cutoff["points"]
                    st.success(
                        f"{selected_name} is currently inside the predicted invite line with a "
                        f"{selected_invite_team['points'] - comparison:+,} point cushion."
                    )
                else:
                    points_needed = max(
                        0, cutoff["points"] - selected_invite_team["points"] + 1
                    )
                    st.warning(
                        f"{selected_name} is outside the predicted invite line and needs roughly "
                        f"{points_needed:,} more points than the current cutoff."
                    )

            cutoff_points = cutoff["points"] if cutoff else None
            race_table = pd.DataFrame(
                {
                    "Rank": [row["rank"] for row in track_rows],
                    "Team": [row["team"] for row in track_rows],
                    "Points": [row["points"] for row in track_rows],
                    "Status": [row["status"] for row in track_rows],
                    "Gap to cutoff": [
                        row["points"] - cutoff_points if cutoff_points is not None else None
                        for row in track_rows
                    ],
                    "Roster": [" · ".join(row["roster"]) for row in track_rows],
                }
            )
            st.dataframe(
                race_table,
                width="stretch",
                hide_index=True,
                height=620,
                column_config={
                    "Rank": st.column_config.NumberColumn(format="#%d"),
                    "Points": st.column_config.NumberColumn(format="%d"),
                    "Gap to cutoff": st.column_config.NumberColumn(format="%+d"),
                },
            )
            st.link_button("Open this prediction on HLTV", chosen_event["event_url"])
            st.markdown(
                """
                <div class="disclaimer">
                  HLTV labels this as a prediction of the ranking on the invite date. It looks
                  six months back, applies time decay and may include secured winnings from
                  unfinished events. The official invite position can still change with every
                  result and with Valve's full network recalculation.
                </div>
                """,
                unsafe_allow_html=True,
            )

with rankings_tab:
    st.subheader(f"Global standings · {snapshot['date'].replace('_', '-')}")
    st.caption(snapshot.get("source", "Valve official snapshot"))
    rankings_df = pd.DataFrame(
        {
            "Rank": [row["rank"] for row in standings],
            "Team": [row["team"] for row in standings],
            "Points": [row["points"] for row in standings],
            "Current roster": [" · ".join(row["roster"]) for row in standings],
        }
    )
    st.dataframe(
        rankings_df,
        width="stretch",
        hide_index=True,
        height=650,
        column_config={
            "Rank": st.column_config.NumberColumn(format="#%d"),
            "Points": st.column_config.NumberColumn(format="%d"),
        },
    )

with method_tab:
    st.subheader("What the app can — and cannot — calculate")
    st.markdown(
        """
        **Official score.** The headline score, factors and contributing matches come directly from
        **HLTV's live VRS Beta**, which updates between Valve's official monthly snapshots and includes
        secured prize money from unfinished events.

        **Official reference.** Valve's public Regional Standings repository remains the fallback and
        is used to enrich older matches with their historical five-player lineups. Newer events are
        matched to the lineup shown on their HLTV match pages.

        **Roster identity.** Valve's model treats a past lineup as the same ranked entity when
        it shares at least **three players** with the newer lineup. The simulator applies that rule to
        the listed historical contributions.

        **Indicative score.** The live point rows allow a much closer inheritance estimate, grouped by
        event. It is still not an official reranking: changing a roster also changes the global opponent
        network, top-ten selection and head-to-head recalculation.

        **Timeline.** The no-new-results curve keeps a contribution at full recency weight for 30 days
        and then decays it linearly to zero by day 183. It isolates timing and roster inheritance, but
        cannot predict new results or Valve's future global network.

        **Invite race.** Upcoming event dates, predicted rankings and qualification lines come from
        HLTV's VRS invite pages. These are forecasts for the invite date, not confirmed invitations.

        **Missing lineup safety.** A historical result is never assigned the current roster by default.
        If neither source can verify its lineup, it is marked **Unknown** and no simulated score is shown
        until the missing history can be resolved.
        """
    )
    link_left, link_middle, link_right = st.columns(3)
    with link_left:
        st.link_button("Open HLTV's live VRS", "https://www.hltv.org/valve-ranking/teams")
    with link_middle:
        st.link_button(
            "Open HLTV's invite predictions",
            "https://www.hltv.org/valve-ranking/invites",
        )
    with link_right:
        st.link_button(
            "Open Valve's official VRS repository",
            "https://github.com/ValveSoftware/counter-strike_regional_standings",
        )
