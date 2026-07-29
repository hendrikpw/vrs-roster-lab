from __future__ import annotations

import html
from datetime import date, datetime, timedelta
import altair as alt
import pandas as pd
import streamlit as st

from pro_data import (
    CURRENT_POOL_EFFECTIVE_FROM,
    ProDataError,
    compare_players,
    load_active_map_pool,
    load_player_profile,
    load_team_map_data,
    opponent_rank_summary,
    predict_veto,
)
from role_data import load_rdy_role_profile
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
        border: 1px solid var(--line); border-top: 4px solid var(--red);
        padding: 20px 22px; margin: 16px 0 18px;
        background: rgba(255,255,255,.18);
    }
    .sim-panel h2 { font-size: 34px; margin: 0 0 4px; }
    .panel-copy { color: var(--muted); font-size: 14px; }
    .impact {
        margin-top: 18px; padding: 18px 20px;
        border: 1px solid var(--line); background: rgba(255,255,255,.18);
    }
    .impact-number { font: 700 58px/.95 "Oswald", sans-serif; color: var(--red); }
    .impact-number.positive { color: var(--green); }
    .impact-number.neutral { color: var(--ink); }
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
        .sim-panel { padding: 18px; margin-top: 12px; }
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_player_profile(query: str, days: int, data_model_version: str):
    return load_player_profile(query, days)


@st.cache_data(ttl=21600, show_spinner=False)
def get_rdy_role_profile(query: str):
    return load_rdy_role_profile(query)


@st.cache_data(ttl=3600, show_spinner=False)
def get_team_map_profile(
    query: str,
    days: int,
    start_date: str | None,
    data_model_version: str,
):
    return load_team_map_data(
        query,
        days,
        start_date=date.fromisoformat(start_date) if start_date else None,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_active_map_pool(data_model_version: str):
    return load_active_map_pool()


def resolve_team_detail(team_row: dict) -> dict:
    """Load one ranked team's richest available VRS detail."""
    if team_row.get("source") == "HLTV Live VRS (Beta)":
        official_detail = None
        try:
            _, official_rows = get_official_standings()
            official_row = next(
                (
                    row
                    for row in official_rows
                    if row["team"].casefold() == team_row["team"].casefold()
                ),
                None,
            )
            if official_row and official_row["detail_url"]:
                official_detail = get_official_detail(official_row["detail_url"])
        except VRSDataError:
            pass
        return get_live_detail(team_row, official_detail, DATA_MODEL_VERSION)

    if not team_row.get("detail_url"):
        raise VRSDataError(f"No VRS detail is available for {team_row['team']}.")
    return get_official_detail(team_row["detail_url"])


@st.dialog("How VRS works", width="large")
def show_vrs_guide():
    st.markdown(
        """
        VRS is Valve's ranking score for deciding invitations and seeding. A result does
        **not** award one fixed number of VRS points. The full ranking is recalculated
        from several signals.
        """
    )

    st.markdown("### What a win can improve")
    st.markdown(
        """
        | Signal | Simple meaning |
        |---|---|
        | **Head-to-head** | Beating a stronger team helps more than beating a weaker team. |
        | **Opponent network** | Wins over teams with strong results are worth more. |
        | **Bounty collected** | The opponent's recent prize-money strength matters. |
        | **LAN wins** | Relevant offline wins provide additional support. |
        """
    )

    st.markdown("### Simple example")
    example_left, example_middle, example_right = st.columns(3)
    example_left.metric("Before the match", "1,600 VRS")
    example_middle.metric("Match-history row", "+22 H2H")
    example_right.metric("Example reranking", "1,635 VRS", "+35")

    st.info(
        "A team with 1,600 VRS beats a stronger opponent in a LAN BO3. The match may "
        "show **+22 H2H**, but that is only the head-to-head adjustment — not +22 VRS. "
        "After LAN, opponent and bounty support plus the global recalculation, the "
        "illustrative final change is +35 VRS."
    )
    st.caption(
        "The numbers are an example, not a prediction. Exact impact depends on the "
        "full global field, result age, event weight and which results remain in each "
        "team's top ten."
    )

    st.markdown("### Why the impact can change")
    st.markdown(
        """
        - Only the best relevant results are retained, so a new result can replace an older one.
        - Results lose weight with age.
        - Every opponent's results can affect the network.
        - The final scores are normalized across the global ranking.
        """
    )

    st.markdown("### Roster changes: the 3/5 rule")
    st.markdown(
        """
        Historical results stay with the ranked team while at least **three of the five
        players** from that result remain in the new roster.

        - **One replacement:** 4/5 remain → the result stays.
        - **Two replacements:** 3/5 remain → the result still stays, but is at risk.
        - **Three replacements:** only 2/5 remain → the result no longer carries over.

        This applies immediately. The new lineup does not need to play five matches
        before the old results can be checked for roster eligibility.
        """
    )

    st.warning(
        "Remember: **H2H adjustment is not VRS points earned.** The app labels exact "
        "official scores separately from estimates and roster-inheritance simulations."
    )


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

guide_spacer, guide_action = st.columns([5.5, 1])
with guide_action:
    if st.button(
        "HOW VRS WORKS",
        icon=":material/help_outline:",
        width="stretch",
        key="open_vrs_guide",
    ):
        show_vrs_guide()

team_names = [row["team"] for row in standings]
selected_name = st.selectbox(
    "Select a ranked team",
    team_names,
    index=0,
    help="Teams from HLTV's current live VRS calculation.",
)
selected = next(row for row in standings if row["team"] == selected_name)

try:
    detail = fallback_detail if using_fallback else resolve_team_detail(selected)
except VRSDataError:
    detail = fallback_detail
    using_fallback = True

if using_fallback:
    st.warning("Live HLTV and official Valve data are temporarily unavailable. Showing the bundled FaZe demo.")

(
    analysis_tab,
    timeline_tab,
    invite_tab,
    transfer_tab,
    veto_tab,
    rankings_tab,
    method_tab,
) = st.tabs(
    [
        "TEAM ANALYSIS",
        "VRS TIMELINE",
        "INVITE RACE",
        "TRANSFER LAB",
        "MAP VETO",
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
            </div>
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
            placeholder="Enter comma-separated player nicknames",
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
        impact_class = "positive" if delta is not None and delta > 0 else "neutral" if delta == 0 else ""
        st.markdown(
            f"""
              <div class="impact">
                <div class="impact-number {impact_class}">{delta_text}</div>
                <div class="impact-label">indicative VRS change</div>
                <div class="formula">{detail['final_score']:,.0f} → {score_text}</div>
                <div class="impact-label">{simulation['lost_matches']} matches lost · {simulation['fragile_matches']} at the 3/5 threshold{unknown_text}</div>
              </div>
              <div class="disclaimer">
                This is an inheritance estimate, not an official reranking. Exact VRS requires Valve's
                full global network, top-ten selection and normalization to be recalculated.
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
            match_rows["H2H adjustment"] = match_rows["h2h"].map(
                lambda value: f"{value:+.2f}"
            )
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
                    "H2H adjustment",
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
                column_config={
                    "H2H adjustment": st.column_config.TextColumn(
                        help=(
                            "One component of the VRS model. This is not the number "
                            "of VRS points earned from the match."
                        )
                    ),
                },
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
    st.subheader("VRS timeline comparison")
    st.caption(
        "Compare up to five teams on one timeline. Add an optional dated roster scenario "
        "for each team to see when historical results would stop carrying over."
    )
    comparison_team_names = st.multiselect(
        "Teams to compare",
        team_names,
        default=[selected_name],
        max_selections=5,
        key="timeline_comparison_teams",
        help="Choose up to five teams from the current live VRS ranking.",
    )

    comparison_details: dict[str, dict] = {}
    unavailable_teams: list[str] = []
    for comparison_name in comparison_team_names:
        try:
            comparison_detail = (
                detail
                if comparison_name == selected_name
                else resolve_team_detail(
                    next(row for row in standings if row["team"] == comparison_name)
                )
            )
        except VRSDataError:
            unavailable_teams.append(comparison_name)
            continue
        if comparison_detail.get("contributions"):
            comparison_details[comparison_name] = comparison_detail
        else:
            unavailable_teams.append(comparison_name)

    if unavailable_teams:
        st.warning(
            "Live contribution data is unavailable for: "
            + ", ".join(unavailable_teams)
            + "."
        )

    if not comparison_team_names:
        st.info("Select at least one team to build the comparison.")
    elif not comparison_details:
        st.info(
            "Timeline projections require HLTV's live contribution rows and are unavailable "
            "while the app is using an official or bundled fallback snapshot."
        )
    else:
        snapshot_days = {
            team_name: datetime.strptime(
                team_detail["snapshot_date"].replace("_", "-"), "%Y-%m-%d"
            ).date()
            for team_name, team_detail in comparison_details.items()
        }
        latest_snapshot_day = max(snapshot_days.values())
        target_date = st.date_input(
            "Comparison date",
            value=latest_snapshot_day + timedelta(days=30),
            min_value=latest_snapshot_day,
            max_value=latest_snapshot_day + timedelta(days=183),
            help="The summary table compares all selected teams on this date.",
            key="timeline_comparison_date",
        )

        st.markdown("#### Roster scenarios")
        st.caption(
            "Open a team, enable a change and set the exact date. The chart keeps the "
            "current-roster path before that date and applies the new roster afterwards."
        )
        team_scenarios: dict[str, dict] = {}
        for team_name, team_detail in comparison_details.items():
            team_key = f"timeline_team_{team_detail['global_rank']}"
            with st.expander(
                f"{team_name} · {team_detail['final_score']:,.0f} VRS",
                expanded=len(comparison_details) == 1,
            ):
                enable_change = st.checkbox(
                    "Simulate a roster change",
                    key=f"{team_key}_enabled",
                )
                if enable_change:
                    roster_col, replacement_col, date_col = st.columns(
                        [1.25, 1.25, 0.9],
                        gap="medium",
                    )
                    with roster_col:
                        team_leaving = st.multiselect(
                            "Players leaving",
                            team_detail["roster"],
                            key=f"{team_key}_leaving",
                        )
                    with replacement_col:
                        replacements_text = st.text_input(
                            "Replacement players",
                            placeholder="Comma-separated nicknames",
                            key=f"{team_key}_replacements",
                        )
                    with date_col:
                        team_change_date = st.date_input(
                            "Change date",
                            value=snapshot_days[team_name],
                            min_value=snapshot_days[team_name],
                            max_value=snapshot_days[team_name] + timedelta(days=183),
                            key=f"{team_key}_change_date",
                        )
                    team_replacements = [
                        name.strip()
                        for name in replacements_text.split(",")
                        if name.strip()
                    ]
                else:
                    team_leaving = []
                    team_replacements = []
                    team_change_date = snapshot_days[team_name]

                team_scenarios[team_name] = {
                    "leaving": team_leaving,
                    "replacements": team_replacements,
                    "change_date": team_change_date,
                    "changes_requested": bool(team_leaving or team_replacements),
                }

        chart_records: list[dict] = []
        marker_records: list[dict] = []
        comparison_point_records: list[dict] = []
        summary_records: list[dict] = []
        incomplete_scenarios: list[str] = []
        change_notes: list[str] = []

        for team_name, team_detail in comparison_details.items():
            scenario = team_scenarios[team_name]
            timeline = build_vrs_timeline(
                team_detail,
                scenario["leaving"],
                scenario["replacements"],
                change_date=scenario["change_date"],
            )
            scenario_label = (
                "Planned roster"
                if scenario["changes_requested"]
                else "Current roster"
            )
            for row in timeline["rows"]:
                chart_records.append(
                    {
                        "Date": row["date"],
                        "Team": team_name,
                        "VRS": row["scenario_score"],
                        "Path": scenario_label,
                    }
                )
                if scenario["changes_requested"]:
                    chart_records.append(
                        {
                            "Date": row["date"],
                            "Team": team_name,
                            "VRS": row["baseline_score"],
                            "Path": "Same-roster baseline",
                        }
                    )

            projection = project_vrs(
                team_detail,
                target_date,
                scenario["leaving"],
                scenario["replacements"],
            )
            change_is_active = (
                scenario["changes_requested"]
                and target_date >= scenario["change_date"]
            )
            scenario_score = (
                projection["projected_score"]
                if change_is_active
                else projection["baseline_score"]
            )
            roster_impact = (
                scenario_score - projection["baseline_score"]
                if scenario_score is not None
                else None
            )
            outgoing = ", ".join(scenario["leaving"]) or "—"
            incoming = ", ".join(scenario["replacements"]) or "—"
            change_description = (
                f"{scenario['change_date'].isoformat()} · {outgoing} → {incoming}"
                if scenario["changes_requested"]
                else "No change"
            )
            summary_records.append(
                {
                    "Team": team_name,
                    "Current VRS": team_detail["final_score"],
                    "Same-roster baseline": projection["baseline_score"],
                    "Scenario VRS": scenario_score,
                    "Roster impact": roster_impact,
                    "Roster scenario": change_description,
                }
            )
            if scenario_score is not None:
                chart_records.append(
                    {
                        "Date": target_date.isoformat(),
                        "Team": team_name,
                        "VRS": scenario_score,
                        "Path": scenario_label,
                    }
                )
                if scenario["changes_requested"]:
                    chart_records.append(
                        {
                            "Date": target_date.isoformat(),
                            "Team": team_name,
                            "VRS": projection["baseline_score"],
                            "Path": "Same-roster baseline",
                        }
                    )
                comparison_point_records.append(
                    {
                        "Date": target_date.isoformat(),
                        "Team": team_name,
                        "VRS": scenario_score,
                        "Same-roster baseline": projection["baseline_score"],
                        "Roster impact": roster_impact,
                        "Roster scenario": change_description,
                    }
                )

            if scenario["changes_requested"]:
                marker_projection = project_vrs(
                    team_detail,
                    scenario["change_date"],
                    scenario["leaving"],
                    scenario["replacements"],
                )
                marker_score = marker_projection["projected_score"]
                marker_records.append(
                    {
                        "Date": scenario["change_date"].isoformat(),
                        "Team": team_name,
                        "VRS": marker_score,
                        "Change": f"{outgoing} → {incoming}",
                    }
                )
                if marker_score is None:
                    incomplete_scenarios.append(team_name)
                else:
                    change_notes.append(
                        f"**{team_name}:** {scenario['change_date'].isoformat()} · "
                        f"{outgoing} → {incoming}"
                    )

        chart_data = pd.DataFrame(chart_records)
        chart_data["Date"] = pd.to_datetime(chart_data["Date"])
        chart_data = (
            chart_data.drop_duplicates(
                subset=["Date", "Team", "Path"],
                keep="last",
            )
            .sort_values(["Team", "Path", "Date"])
        )
        team_domain = list(comparison_details)
        team_colors = ["#e23a32", "#2e7d5b", "#d89b2b", "#386a8c", "#7d4f96"]
        color_encoding = alt.Color(
            "Team:N",
            scale=alt.Scale(domain=team_domain, range=team_colors[: len(team_domain)]),
            legend=alt.Legend(title="Team"),
        )
        timeline_chart = (
            alt.Chart(chart_data)
            .mark_line(strokeWidth=3)
            .encode(
                x=alt.X("Date:T", title=None),
                y=alt.Y(
                    "VRS:Q",
                    title="VRS points",
                    scale=alt.Scale(zero=False),
                ),
                color=color_encoding,
                strokeDash=alt.StrokeDash(
                    "Path:N",
                    scale=alt.Scale(
                        domain=[
                            "Current roster",
                            "Planned roster",
                            "Same-roster baseline",
                        ],
                        range=[[1, 0], [1, 0], [7, 5]],
                    ),
                    legend=alt.Legend(title="Path"),
                ),
                detail=["Team:N", "Path:N"],
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Path:N"),
                    alt.Tooltip("Date:T", format="%Y-%m-%d"),
                    alt.Tooltip("VRS:Q", format=",.0f"),
                ],
            )
        )
        hover_targets = (
            alt.Chart(chart_data)
            .mark_point(size=120, opacity=0.001)
            .encode(
                x="Date:T",
                y="VRS:Q",
                color=color_encoding,
                detail=["Team:N", "Path:N"],
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Path:N"),
                    alt.Tooltip("Date:T", format="%Y-%m-%d"),
                    alt.Tooltip("VRS:Q", title="VRS points", format=",.0f"),
                ],
            )
        )
        timeline_chart = timeline_chart + hover_targets

        if comparison_point_records:
            comparison_points_data = pd.DataFrame(comparison_point_records)
            comparison_points_data["Date"] = pd.to_datetime(
                comparison_points_data["Date"]
            )
            comparison_date_rule = (
                alt.Chart(pd.DataFrame({"Date": [pd.Timestamp(target_date)]}))
                .mark_rule(color="#6d685e", strokeDash=[5, 5], strokeWidth=2)
                .encode(x="Date:T")
            )
            comparison_points = (
                alt.Chart(comparison_points_data)
                .mark_point(
                    filled=True,
                    shape="circle",
                    size=190,
                    stroke="#f3f0e8",
                    strokeWidth=3,
                )
                .encode(
                    x="Date:T",
                    y="VRS:Q",
                    color=color_encoding,
                    tooltip=[
                        alt.Tooltip("Team:N"),
                        alt.Tooltip(
                            "Date:T",
                            title="Comparison date",
                            format="%Y-%m-%d",
                        ),
                        alt.Tooltip("VRS:Q", title="Scenario VRS", format=",.0f"),
                        alt.Tooltip(
                            "Same-roster baseline:Q",
                            format=",.0f",
                        ),
                        alt.Tooltip(
                            "Roster impact:Q",
                            format="+,.0f",
                        ),
                        alt.Tooltip("Roster scenario:N"),
                    ],
                )
            )
            timeline_chart = (
                timeline_chart + comparison_date_rule + comparison_points
            )

        if marker_records:
            marker_data = pd.DataFrame(marker_records)
            marker_data = marker_data.dropna(subset=["VRS"])
            marker_data["Date"] = pd.to_datetime(marker_data["Date"])
            if not marker_data.empty:
                change_markers = (
                    alt.Chart(marker_data)
                    .mark_point(filled=True, shape="diamond", size=150, stroke="#151515")
                    .encode(
                        x="Date:T",
                        y="VRS:Q",
                        color=color_encoding,
                        tooltip=[
                            alt.Tooltip("Team:N"),
                            alt.Tooltip("Date:T", title="Roster change", format="%Y-%m-%d"),
                            alt.Tooltip("Change:N"),
                            alt.Tooltip("VRS:Q", format=",.0f"),
                        ],
                    )
                )
                timeline_chart = timeline_chart + change_markers

        st.altair_chart(
            timeline_chart.properties(height=460).interactive(),
            width="stretch",
        )

        if change_notes:
            st.markdown(" · ".join(change_notes))
        if incomplete_scenarios:
            st.warning(
                "The changed-roster projection is unavailable for "
                + ", ".join(sorted(set(incomplete_scenarios)))
                + " because some historical contribution rows have no verified lineup."
            )

        comparison_table = pd.DataFrame(summary_records).sort_values(
            "Scenario VRS",
            ascending=False,
            na_position="last",
        )
        st.markdown(f"#### Comparison on {target_date.isoformat()}")
        ranked_rows = comparison_table.dropna(subset=["Scenario VRS"]).to_dict(
            orient="records"
        )
        if ranked_rows:
            comparison_columns = st.columns(len(ranked_rows))
            for rank, (column, row) in enumerate(
                zip(comparison_columns, ranked_rows),
                start=1,
            ):
                impact = row["Roster impact"]
                delta_text = (
                    f"{impact:+,.0f} roster impact"
                    if impact
                    else "same-roster path"
                )
                column.metric(
                    f"#{rank} · {row['Team']}",
                    f"{row['Scenario VRS']:,.0f} VRS",
                    delta_text,
                    delta_color="normal" if impact else "off",
                )
        st.dataframe(
            comparison_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Current VRS": st.column_config.NumberColumn(format="%.0f"),
                "Same-roster baseline": st.column_config.NumberColumn(format="%.0f"),
                "Scenario VRS": st.column_config.NumberColumn(format="%.0f"),
                "Roster impact": st.column_config.NumberColumn(format="%+.0f"),
            },
        )
        st.markdown(
            """
            <div class="disclaimer">
              Diamond markers indicate scheduled roster changes. Solid lines show each selected
              scenario; dashed lines show where the same team would project with its current
              roster. The model assumes no new matches: existing results retain full recency
              weight for 30 days and decay linearly to zero by day 183. This is an explanatory
              comparison, not an official future ranking.
            </div>
            """,
            unsafe_allow_html=True,
        )

with invite_tab:
    st.subheader("Tournament invite race")
    st.caption(
        "Compare today's live VRS with HLTV's projected ranking at an upcoming "
        "tournament invite date. The qualification line is event- and region-specific."
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

            projection_date = invite_ranking["ranking_date"]
            st.info(
                f"This table is HLTV's projection for **{projection_date}**, not today's "
                "live ranking. The comparison columns below show both values."
            )
            cutoff_points = cutoff["points"] if cutoff else None
            current_points_by_team = {
                row["team"].casefold(): row["points"] for row in standings
            }
            projected_points = [row["points"] for row in track_rows]
            current_live_points = [
                current_points_by_team.get(row["team"].casefold())
                for row in track_rows
            ]
            race_table = pd.DataFrame(
                {
                    "Projected rank": [row["rank"] for row in track_rows],
                    "Team": [row["team"] for row in track_rows],
                    "Current live VRS": current_live_points,
                    f"Projected VRS on {projection_date}": projected_points,
                    "Change by invite date": [
                        (
                            projected - current
                            if current is not None
                            else None
                        )
                        for projected, current in zip(
                            projected_points,
                            current_live_points,
                        )
                    ],
                    "Status": [row["status"] for row in track_rows],
                    "Gap to projected cutoff": [
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
                    "Projected rank": st.column_config.NumberColumn(format="#%d"),
                    "Current live VRS": st.column_config.NumberColumn(
                        format="%d",
                        help="Current value from HLTV's live Valve ranking.",
                    ),
                    f"Projected VRS on {projection_date}": st.column_config.NumberColumn(
                        format="%d",
                        help=(
                            "HLTV's predicted value at the selected tournament's "
                            "invite date."
                        ),
                    ),
                    "Change by invite date": st.column_config.NumberColumn(
                        format="%+d",
                        help="Projected VRS minus current live VRS.",
                    ),
                    "Gap to projected cutoff": st.column_config.NumberColumn(
                        format="%+d"
                    ),
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

with transfer_tab:
    st.subheader(f"Transfer candidate comparison · {detail['team']}")
    st.caption(
        "Compare a current player with a potential replacement, then place the sporting "
        "difference next to the modeled VRS inheritance impact."
    )
    transfer_controls = st.columns([0.8, 1.2, 0.7])
    with transfer_controls[0]:
        outgoing_player = st.selectbox(
            "Current player",
            detail["roster"],
            key="transfer_outgoing_player",
        )
    with transfer_controls[1]:
        candidate_query = st.text_input(
            "Candidate",
            placeholder="Enter a professional player nickname",
            key="transfer_candidate_query",
            help="Enter a professional player's nickname. The closest exact BO3.gg profile is used.",
        )
    with transfer_controls[2]:
        comparison_window = st.selectbox(
            "Stats window",
            [90, 180],
            index=1,
            format_func=lambda days: f"Last {days // 30} months",
            key="transfer_stats_window",
        )

    if not candidate_query.strip():
        st.info("Enter a candidate nickname to run the sporting and VRS comparison.")
    else:
        try:
            with st.spinner("Loading pro-play statistics…"):
                current_profile = get_player_profile(
                    outgoing_player, comparison_window, DATA_MODEL_VERSION
                )
                candidate_profile = get_player_profile(
                    candidate_query.strip(), comparison_window, DATA_MODEL_VERSION
                )
            player_comparison = compare_players(current_profile, candidate_profile)
        except ProDataError as exc:
            player_comparison = None
            st.warning(str(exc))

        if player_comparison:
            current_name = current_profile["nickname"]
            candidate_name = candidate_profile["nickname"]
            st.markdown(
                f"**Resolved comparison:** {current_name} ({current_profile['team']}) "
                f"→ {candidate_name} ({candidate_profile['team']})"
            )
            transfer_metrics = st.columns(5)
            current_rating = current_profile["metrics"]["BO3 rating"]
            candidate_rating = candidate_profile["metrics"]["BO3 rating"]
            rating_delta = (
                candidate_rating - current_rating
                if current_rating is not None and candidate_rating is not None
                else None
            )
            transfer_metrics[0].metric(
                f"{current_name} rating",
                f"{current_rating:.2f}" if current_rating is not None else "Unknown",
            )
            transfer_metrics[1].metric(
                f"{candidate_name} rating",
                f"{candidate_rating:.2f}" if candidate_rating is not None else "Unknown",
                f"{rating_delta:+.2f}" if rating_delta is not None else None,
            )
            candidate_adr = candidate_profile["metrics"]["ADR"]
            transfer_metrics[2].metric(
                f"{candidate_name} ADR",
                f"{candidate_adr:.1f}" if candidate_adr is not None else "Unknown",
            )
            opening = candidate_profile["metrics"]["Opening duel win %"]
            transfer_metrics[3].metric(
                "Opening duel win",
                f"{opening:.1%}" if opening is not None else "Unknown",
            )
            role_fit_summary = player_comparison["role_fit"]["score"]
            transfer_metrics[4].metric(
                "Role fit · provisional",
                f"{role_fit_summary:.0f} / 100"
                if role_fit_summary is not None
                else "Unknown",
                help=(
                    "Weighted statistical role similarity across opening involvement, "
                    "trading, assists, survival, headshots and opening success."
                ),
            )

            def display_player_metric(metric: str, value):
                if value is None:
                    return "Unknown"
                if "%" in metric:
                    return f"{value:.1%}"
                if metric in {"Maps", "Rounds", "Clutches"}:
                    return f"{value:,.0f}"
                if metric in {"ADR"}:
                    return f"{value:.1f}"
                return f"{value:.3f}"

            comparison_rows = pd.DataFrame(
                {
                    "Metric": [row["metric"] for row in player_comparison["metrics"]],
                    current_name: [
                        display_player_metric(row["metric"], row["current"])
                        for row in player_comparison["metrics"]
                    ],
                    candidate_name: [
                        display_player_metric(row["metric"], row["candidate"])
                        for row in player_comparison["metrics"]
                    ],
                }
            )
            st.dataframe(
                comparison_rows,
                width="stretch",
                hide_index=True,
            )

            st.subheader("Map-by-map performance")
            map_rows = pd.DataFrame(player_comparison["maps"])
            if not map_rows.empty:
                st.dataframe(
                    map_rows.rename(
                        columns={
                            "map": "Map",
                            "current_maps": f"{current_name} maps",
                            "current_rating": f"{current_name} rating",
                            "candidate_maps": f"{candidate_name} maps",
                            "candidate_rating": f"{candidate_name} rating",
                            "rating_delta": "Candidate delta",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        f"{current_name} rating": st.column_config.NumberColumn(format="%.2f"),
                        f"{candidate_name} rating": st.column_config.NumberColumn(format="%.2f"),
                        "Candidate delta": st.column_config.NumberColumn(format="%+.2f"),
                    },
                )

            role_fit = player_comparison["role_fit"]
            st.subheader("Statistical role fit")
            st.caption(
                "Measures how closely the candidate mirrors the outgoing player's statistical "
                "job. This is a role-similarity score, not a rating of who is the better player."
            )
            fit_columns = st.columns(4)
            role_score = role_fit["score"]
            fit_columns[0].metric(
                "Role fit",
                f"{role_score:.0f} / 100" if role_score is not None else "Unavailable",
            )
            fit_columns[1].metric("Interpretation", role_fit["label"])
            fit_columns[2].metric(
                "Sample confidence",
                role_fit["confidence_label"],
                f"{role_fit['confidence_score']:.0f} / 100",
                help=(
                    "Confidence uses the smaller sample of the two players, based on rounds, "
                    "maps and available comparison fields. It does not change the fit score."
                ),
                delta_color="off",
            )
            fit_columns[3].metric(
                "Indicators compared",
                f"{role_fit['compared_metrics']} / {role_fit['total_metrics']}",
                f"{role_fit['minimum_maps']} maps · {role_fit['minimum_rounds']} rounds",
                delta_color="off",
            )
            if role_score is not None:
                st.progress(role_score / 100)

            role_rows = pd.DataFrame(
                [
                    {
                        "Indicator": row["indicator"],
                        current_name: f"{row['current']:.1%}",
                        candidate_name: f"{row['candidate']:.1%}",
                        "Difference": f"{row['difference']:+.1%}",
                        "Weight": f"{row['weight']:.0%}",
                        "Similarity": f"{row['similarity']:.0%}",
                    }
                    for row in role_fit["breakdown"]
                ]
            )
            if not role_rows.empty:
                st.dataframe(role_rows, width="stretch", hide_index=True)

            with st.expander("How the role-fit score works"):
                st.markdown(
                    """
                    The score compares six observed tendencies. Opening involvement carries
                    the most weight because it strongly describes who takes first-contact
                    responsibility. Trade share, assists and survival describe spacing and
                    support tendencies; headshot share and opening success have smaller weights.

                    Each indicator receives a similarity score from its percentage-point
                    difference. The weighted values are combined and renormalized when a field
                    is unavailable. **Rating, ADR and K/D are deliberately excluded:** they
                    describe performance, not whether two players perform the same job.
                    Exact T-side routes and CT positions are not yet part of the calculation;
                    use the NER0 scout below as the positional cross-check.
                    """
                )

            st.divider()
            st.subheader("Role & position data")
            st.caption(
                "App-owned tables combine RDY's published overall role with BO3.gg tendencies. "
                "Exact map positions remain unavailable until a structured NER0/RDY record exists."
            )

            with st.spinner("Checking published role coverage…"):
                current_role_source = get_rdy_role_profile(current_name)
                candidate_role_source = get_rdy_role_profile(candidate_name)

            role_source_rows = pd.DataFrame(
                [
                    {
                        "Player": player_name,
                        "Overall role": source_profile["overall_role"] or "Unavailable",
                        "Role score": (
                            f"{source_profile['role_score']:.0f}"
                            if source_profile["role_score"] is not None
                            else "—"
                        ),
                        "Team at source": source_profile["team"] or "Unknown",
                        "CT/T map coverage": "0 / 7 structured",
                        "Status": source_profile["status"],
                        "Source": source_profile["source"],
                    }
                    for player_name, source_profile in [
                        (current_name, current_role_source),
                        (candidate_name, candidate_role_source),
                    ]
                ]
            )
            st.dataframe(role_source_rows, width="stretch", hide_index=True)

            tendency_rows = []
            for profile in [current_profile, candidate_profile]:
                profile_metrics = profile["metrics"]
                profile_style = profile["style"]
                tendency_rows.append(
                    {
                        "Player": profile["nickname"],
                        "T round win": (
                            f"{profile_metrics['T round win %']:.1%}"
                            if profile_metrics["T round win %"] is not None
                            else "Unavailable"
                        ),
                        "CT round win": (
                            f"{profile_metrics['CT round win %']:.1%}"
                            if profile_metrics["CT round win %"] is not None
                            else "Unavailable"
                        ),
                        "Opening involvement": (
                            f"{profile_style['Opening involvement']:.1%}"
                            if profile_style["Opening involvement"] is not None
                            else "Unavailable"
                        ),
                        "Opening success": (
                            f"{profile_style['Opening success']:.1%}"
                            if profile_style["Opening success"] is not None
                            else "Unavailable"
                        ),
                        "Trade-kill share": (
                            f"{profile_style['Trade-kill share']:.1%}"
                            if profile_style["Trade-kill share"] is not None
                            else "Unavailable"
                        ),
                        "Assist rate": (
                            f"{profile_style['Assist rate']:.1%}"
                            if profile_style["Assist rate"] is not None
                            else "Unavailable"
                        ),
                        "Survival rate": (
                            f"{profile_style['Survival rate']:.1%}"
                            if profile_style["Survival rate"] is not None
                            else "Unavailable"
                        ),
                        "Sample": (
                            f"{profile_metrics['Maps']} maps · "
                            f"{profile_metrics['Rounds']} rounds"
                        ),
                        "Source": "BO3.gg",
                    }
                )

            st.markdown("#### Side and playstyle tendencies")
            st.dataframe(
                pd.DataFrame(tendency_rows),
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "T/CT round win is the team's round result while the player was in the sampled "
                "lineup. Opening, trading, assist and survival values currently use the complete "
                "sample and are not side-specific."
            )

            st.warning(
                "The positional part of the Role Fit is not scored yet: exact T routes and CT "
                "positions are missing from the structured feeds, so the displayed score remains "
                "provisional instead of treating unknown positions as a match."
            )
            source_links = st.columns(3)
            with source_links[0]:
                st.link_button(
                    "Open NER0 Positions Database",
                    (
                        "https://public.tableau.com/app/profile/harry.richards4213/"
                        "viz/PositionsDatabaseNER0cs/PositionsDatabaseNER0cs"
                    ),
                )
            with source_links[1]:
                st.link_button(
                    "Open RDY Player Positions",
                    "https://rdy.gg/en/cs2/stats?tab=player-positions",
                )
            with source_links[2]:
                st.link_button(
                    "Open RDY Roster Simulator",
                    "https://rdy.gg/en/cs2/stats?tab=roster-simulator",
                )

            st.markdown(
                """
                <div class="disclaimer">
                  Source priority: structured NER0 positions, then RDY positions, then a
                  clearly labelled statistical inference. RDY's current public page is used
                  only for its published overall role. Missing CT/T positions are never guessed.
                  Every value keeps its source and availability status.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.subheader("VRS cost of the transfer")
            transfer_simulation = simulate_roster(
                detail,
                [outgoing_player],
                [candidate_name],
            )
            vrs_columns = st.columns(4)
            vrs_columns[0].metric("Current VRS", f"{detail['final_score']:,.0f}")
            vrs_columns[1].metric(
                "Indicative VRS",
                (
                    f"{transfer_simulation['indicative_score']:,.0f}"
                    if transfer_simulation["indicative_score"] is not None
                    else "Unknown"
                ),
            )
            vrs_columns[2].metric(
                "VRS impact",
                (
                    f"{transfer_simulation['indicative_delta']:+,.0f}"
                    if transfer_simulation["indicative_delta"] is not None
                    else "Unknown"
                ),
            )
            vrs_columns[3].metric(
                "Historical matches lost",
                transfer_simulation["lost_matches"],
            )

            style_rows = []
            for indicator in current_profile["style"]:
                left = current_profile["style"][indicator]
                right = candidate_profile["style"][indicator]
                style_rows.append(
                    {
                        "Playstyle indicator": indicator,
                        current_name: f"{left:.1%}" if left is not None else "Unknown",
                        candidate_name: f"{right:.1%}" if right is not None else "Unknown",
                    }
                )
            with st.expander("Playstyle indicators and unavailable splits"):
                st.dataframe(pd.DataFrame(style_rows), width="stretch", hide_index=True)
                st.markdown(
                    "**Currently unavailable from the stable automated source:** "
                    + ", ".join(player_comparison["unavailable_splits"])
                    + ". These values are shown as unavailable rather than estimated."
                )

            source_left, source_right = st.columns(2)
            with source_left:
                st.link_button(
                    f"Open {current_name} on BO3.gg",
                    current_profile["source_url"],
                )
            with source_right:
                st.link_button(
                    f"Open {candidate_name} on BO3.gg",
                    candidate_profile["source_url"],
                )
            st.markdown(
                """
                <div class="disclaimer">
                  BO3.gg uses its own 10-point player rating; it is not HLTV Rating 3.0.
                  Style similarity describes statistical tendencies, not exact in-game roles,
                  communication, contract availability or buyout cost. The VRS value remains
                  an inheritance estimate using the verified historical lineups.
                </div>
                """,
                unsafe_allow_html=True,
            )

with veto_tab:
    st.subheader("Map veto predictor")
    st.caption(
        "Build a likely veto from recent picks, bans and map results. The prediction is "
        "descriptive and does not use betting odds."
    )
    veto_controls = st.columns([1, 1, 0.55, 0.55, 0.55])
    with veto_controls[0]:
        team_a_name = st.selectbox(
            "Team A",
            team_names,
            index=team_names.index(selected_name),
            key="veto_team_a",
        )
    opponent_options = [name for name in team_names if name != selected_name]
    default_opponent = opponent_options[0] if opponent_options else selected_name
    with veto_controls[1]:
        team_b_name = st.selectbox(
            "Team B",
            team_names,
            index=team_names.index(default_opponent),
            key="veto_team_b",
        )
    with veto_controls[2]:
        veto_window = st.selectbox(
            "Form",
            ["Current pool era", "3 months", "6 months"],
            index=0,
            key="veto_window",
        )
    with veto_controls[3]:
        best_of = st.selectbox(
            "Format",
            [3, 5],
            format_func=lambda value: f"BO{value}",
            key="veto_best_of",
        )
    with veto_controls[4]:
        run_veto = st.button(
            "Build veto",
            type="primary",
            width="stretch",
        )

    if team_a_name == team_b_name:
        st.warning("Choose two different teams.")
    elif run_veto:
        try:
            veto_days = {"Current pool era": 180, "3 months": 90, "6 months": 180}[
                veto_window
            ]
            veto_start_date = (
                CURRENT_POOL_EFFECTIVE_FROM.isoformat()
                if veto_window == "Current pool era"
                else None
            )
            with st.spinner("Loading recent maps and vetoes…"):
                active_map_pool = get_active_map_pool(DATA_MODEL_VERSION)
                team_a_data = get_team_map_profile(
                    team_a_name,
                    veto_days,
                    veto_start_date,
                    DATA_MODEL_VERSION,
                )
                team_b_data = get_team_map_profile(
                    team_b_name,
                    veto_days,
                    veto_start_date,
                    DATA_MODEL_VERSION,
                )
            st.session_state["veto_result"] = {
                "key": (team_a_name, team_b_name, veto_window, best_of),
                "team_a": team_a_data,
                "team_b": team_b_data,
                "prediction": predict_veto(
                    team_a_data,
                    team_b_data,
                    best_of,
                    active_map_pool,
                ),
            }
        except ProDataError as exc:
            st.warning(str(exc))

    stored_veto = st.session_state.get("veto_result")
    current_veto_key = (team_a_name, team_b_name, veto_window, best_of)
    if not stored_veto or stored_veto.get("key") != current_veto_key:
        if team_a_name != team_b_name:
            st.info("Press “Build veto” to load the selected matchup.")
    else:
        team_a_data = stored_veto["team_a"]
        team_b_data = stored_veto["team_b"]
        veto_prediction = stored_veto["prediction"]
        st.caption(
            "Current Active Duty pool: "
            + " · ".join(veto_prediction["active_map_pool"])
            + f" · form since {team_a_data['period_start']}"
        )
        a_strength = opponent_rank_summary(team_a_data, standings)
        b_strength = opponent_rank_summary(team_b_data, standings)
        veto_metrics = st.columns(6)
        veto_metrics[0].metric(
            f"{team_a_data['name']} form",
            (
                f"{team_a_data['match_win_rate']:.1%}"
                if team_a_data["match_win_rate"] is not None
                else "Unknown"
            ),
            f"{team_a_data['matches']} series",
        )
        veto_metrics[1].metric(
            f"{team_b_data['name']} form",
            (
                f"{team_b_data['match_win_rate']:.1%}"
                if team_b_data["match_win_rate"] is not None
                else "Unknown"
            ),
            f"{team_b_data['matches']} series",
        )
        veto_metrics[2].metric(
            f"{team_a_data['name']} opponent rank",
            (
                f"#{a_strength['average_rank']:.1f}"
                if a_strength["average_rank"] is not None
                else "Unknown"
            ),
            f"{a_strength['matched']}/{a_strength['total']} ranked",
        )
        veto_metrics[3].metric(
            f"{team_b_data['name']} opponent rank",
            (
                f"#{b_strength['average_rank']:.1f}"
                if b_strength["average_rank"] is not None
                else "Unknown"
            ),
            f"{b_strength['matched']}/{b_strength['total']} ranked",
        )
        veto_metrics[4].metric(
            f"{team_a_data['name']} BO{best_of}",
            f"{veto_prediction['team_a_series_probability']:.1%}",
        )
        veto_metrics[5].metric(
            f"{team_b_data['name']} BO{best_of}",
            f"{veto_prediction['team_b_series_probability']:.1%}",
        )

        st.subheader("Predicted veto sequence")
        st.dataframe(
            pd.DataFrame(veto_prediction["sequence"]).rename(
                columns={
                    "step": "Step",
                    "team": "Team",
                    "action": "Action",
                    "map": "Map",
                }
            ),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Map pool comparison")
        veto_maps = pd.DataFrame(veto_prediction["maps"])
        veto_maps["Selected"] = veto_maps["selected"].map(
            {True: "Played", False: "Removed"}
        )
        st.dataframe(
            veto_maps[
                [
                    "map",
                    "team_a_played",
                    "team_a_win_rate",
                    "team_a_picks",
                    "team_a_bans",
                    "team_b_played",
                    "team_b_win_rate",
                    "team_b_picks",
                    "team_b_bans",
                    "team_a_probability",
                    "Selected",
                ]
            ].rename(
                columns={
                    "map": "Map",
                    "team_a_played": f"{team_a_data['name']} maps",
                    "team_a_win_rate": f"{team_a_data['name']} win rate",
                    "team_a_picks": f"{team_a_data['name']} picks",
                    "team_a_bans": f"{team_a_data['name']} bans",
                    "team_b_played": f"{team_b_data['name']} maps",
                    "team_b_win_rate": f"{team_b_data['name']} win rate",
                    "team_b_picks": f"{team_b_data['name']} picks",
                    "team_b_bans": f"{team_b_data['name']} bans",
                    "team_a_probability": f"{team_a_data['name']} map probability",
                }
            ),
            width="stretch",
            hide_index=True,
            column_config={
                f"{team_a_data['name']} win rate": st.column_config.NumberColumn(
                    format="percent"
                ),
                f"{team_b_data['name']} win rate": st.column_config.NumberColumn(
                    format="percent"
                ),
                f"{team_a_data['name']} map probability": st.column_config.NumberColumn(
                    format="percent"
                ),
            },
        )
        source_a, source_b = st.columns(2)
        with source_a:
            st.link_button(
                f"Open {team_a_data['name']} on BO3.gg",
                team_a_data["source_url"],
            )
        with source_b:
            st.link_button(
                f"Open {team_b_data['name']} on BO3.gg",
                team_b_data["source_url"],
            )
        st.markdown(
            """
            <div class="disclaimer">
              The veto is a heuristic based on recent team-owned picks and bans, smoothed
              map win rates and recent series form. It cannot know an event's private prep,
              stand-ins or one-off tactical choices. Percentages are model estimates, not
              betting probabilities.
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

        **Transfer Lab.** Recent player and map statistics come from BO3.gg because HLTV's regular
        statistics pages block automated Streamlit requests. BO3.gg's 10-point rating is not directly
        comparable with HLTV Rating 3.0. Statistical style similarity is a heuristic, not a role label.

        **Map veto.** The suggested BO3/BO5 veto uses recent team-owned picks and bans, map results,
        smoothed win rates and series form. It cannot account for private preparation, stand-ins or
        event-specific tactics, and its probabilities are not betting odds. The seven-map Active Duty
        pool is loaded dynamically; the default form window begins with the current pool change.

        **Missing lineup safety.** A historical result is never assigned the current roster by default.
        If neither source can verify its lineup, it is marked **Unknown** and no simulated score is shown
        until the missing history can be resolved.
        """
    )
    link_left, link_middle, link_pro, link_right = st.columns(4)
    with link_left:
        st.link_button("Open HLTV's live VRS", "https://www.hltv.org/valve-ranking/teams")
    with link_middle:
        st.link_button(
            "Open HLTV's invite predictions",
            "https://www.hltv.org/valve-ranking/invites",
        )
    with link_pro:
        st.link_button("Open BO3.gg pro statistics", "https://bo3.gg/")
    with link_right:
        st.link_button(
            "Open Valve's official VRS repository",
            "https://github.com/ValveSoftware/counter-strike_regional_standings",
        )
