import unittest
from datetime import date

from vrs_data import (
    DATA_MODEL_VERSION,
    build_vrs_timeline,
    parse_hltv_invite_ranking,
    parse_hltv_invites,
    parse_hltv_standings,
    parse_hltv_match_roster,
    parse_hltv_result_links,
    parse_hltv_team_detail,
    parse_standings,
    parse_team_detail,
    project_vrs,
    recency_weight,
    simulate_roster,
)


STANDINGS = """### Standings as of 2026_07_06<br />
| Standing | Points | Team Name | Roster | |
| :- | -: | :- | :- | :- |
| 23 | 1404 | FaZe | broky, frozen, jcobbb, Neityu, Twistzz | [details](details/2026_07_06/faze.md) |
"""


DETAIL = """### Roster Details<br />
Team Name: FaZe<br />
Roster: broky, frozen, jcobbb, Neityu, Twistzz<br />
Global Rank: 23<br />
Region: Europe<br />
Regional Rank: 16<br />
Final Rank Value: 1404.5<br />
Final Rank Value (1404.5) = Starting Rank Value (1440.8) + Head To Head Adjustments (-36.4)<br />
- Bounty Offered: 0.663
- Bounty Collected: 0.534
- Opponent Network: 0.229
- LAN Wins: 0.783
| Match Played | Match ID | Date | Opponent | W/L | Age Weight | Event Weight | Bounty Collected | Opponent Network | LAN Wins | H2H Adj. | Roster |
| -: | -: | :- | :- | :- | :- | :- | :- | :- | :- | -: | :- |
| 2 | 681 | 2026-05-30 | NIP | L | 0.953 | - | - | - | - | -18.57 | broky, frozen, jcobbb, Neityu, Twistzz |
| 1 | 2438 | 2026-04-06 | Inner Circle | W | 0.593 | 0.5 | 0.2 (0.1) | 0.4 (0.2) | 1 (0.5) | 7.50 | broky, frozen, jcobbb, karrigan, Twistzz |
| Event Date | Age Weight | Prize Winnings | Scaled Winnings |
| :- | -: | :- | :- |
| 2026-05-30 | 0.954 | $13,500.00 | $12,881.30 |
"""

HLTV_STANDINGS = """Valve global ranking on July 26th, 2026

#15![Image 201: FaZe](https://example.com/faze.png)

FaZe(1629 Valve points)EU

frozen

Twistzz

Neityu

jcobbb

JBOEN

[![Image: frozen](https://example.com/player.png)frozen](https://www.hltv.org/player/9960/frozen)

[HLTV Team profile](https://www.hltv.org/team/6667/faze)[Ranking details](https://www.hltv.org/valve-ranking/teams/details/2026/july/26?lineup=1%2C2%2C3%2C4%2C5&isFuture=false)
"""

HLTV_DETAIL = """Ranking details for FaZe on 26 Jul 2026

LAN wins

463 p

Opponent network Opp. network

182 p

Bounty offered

367 p

Bounty collected

296 p

Head to head H2H

-79 p

Most recent LAN wins

| Date | Opponent | Event | Recency | Pts. |
| --- | --- | --- | --- | --- |
| 10/07/26 | ![Image: BetBoom](https://example.com/a.png)BetBoom | ![Image: XSE](https://example.com/b.png)XSE Pro League | 100% | 55 |

Bounty offered, 10 best prize winnings

| Date | Event | Recency | Prize won | Pts. |
| --- | --- | --- | --- | --- |
| 12/07/26 | ![Image: XSE](https://example.com/b.png)XSE Pro League | 100% | $90,000 | 144 |

Head to head matches

| Date | Opponent | Event | Recency | W/L | Pts. |
| --- | --- | --- | --- | --- | --- |
| 25/07/26 | ![Image: DENDELE](https://example.com/c.png)DENDELE | ![Image: BLAST](https://example.com/d.png)BLAST Bounty | 100% | W | 9 |
"""

HLTV_RESULTS = """Results for July 3rd 2026
[FaZe 2 - 0 SINNERS XSE Pro League](https://www.hltv.org/matches/2395475/faze-vs-sinners-xse-pro-league-guangzhou-2026)
Results for April 5th 2026
[FaZe 1 - 2 BIG HLC](https://www.hltv.org/matches/2393066/faze-vs-big-hlc-belgrade-pro-2026)
"""

HLTV_PLAIN_MATCH = """Match stats
Lineups
FaZe
World rank: #11

karrigan

broky

Twistzz

jcobbb

frozen
BIG
World rank: #31
tabseN
JDC
faveN
blameF
gr1ks
"""

HLTV_INVITES = """# Upcoming Events with VRS invite
[![Image](https://example.com/epl.png) EPL S24 12 Invites 12 Global VRS Invites Aug 3rd Invite date](https://www.hltv.org/valve-ranking/teams/event/8244)
[![Image](https://example.com/iem.png) IEM Beijing 29 Invites 22 Global 2 AM 5 AS VRS Invites Aug 3rd Invite date](https://www.hltv.org/valve-ranking/teams/event/8245)
"""

HLTV_INVITE_RANKING = """ESL Pro League Season 24 ranking on August 3rd, 2026

Global

#1![Image: Spirit](https://example.com/spirit.png)

Spirit(2020 Valve points)EU

donk

sh1ro

zont1x

chopper

magixx

#2![Image: G2](https://example.com/g2.png)

G2(1900 Valve points)EU

huNter-

malbsMd

SunPayus

HeavyGod

MATYS

Not qualified

#3![Image: FaZe](https://example.com/faze.png)

FaZe(1650 Valve points)EU

frozen

Twistzz

Neityu

jcobbb

JBOEN
"""


class ParserTests(unittest.TestCase):
    def test_data_model_version_busts_streamlit_cache(self):
        self.assertEqual(DATA_MODEL_VERSION, "timeline-invites-v1")

    def test_standings_parser(self):
        rows = parse_standings(STANDINGS, "live/2026/standings_global_2026_07_06.md")
        self.assertEqual(rows[0]["team"], "FaZe")
        self.assertEqual(rows[0]["points"], 1404)
        self.assertTrue(rows[0]["detail_url"].endswith("live/2026/details/2026_07_06/faze.md"))

    def test_detail_parser(self):
        detail = parse_team_detail(DETAIL)
        self.assertEqual(detail["global_rank"], 23)
        self.assertEqual(len(detail["matches"]), 2)
        self.assertAlmostEqual(detail["matches"][1]["lan_adjusted"], 0.5)
        self.assertEqual(detail["prizes"][0]["prize"], 13500)

    def test_markdown_link_rank_fields(self):
        linked = DETAIL.replace("Global Rank: 23", "Global Rank: [23](../../global.md)")
        linked = linked.replace("Region: Europe", "Region: [Europe](../../europe.md)")
        linked = linked.replace("Regional Rank: 16", "Regional Rank: [16](../../region.md)")
        detail = parse_team_detail(linked)
        self.assertEqual(detail["global_rank"], 23)
        self.assertEqual(detail["regional_rank"], 16)
        self.assertEqual(detail["region"], "Europe")

    def test_hltv_live_standings_parser(self):
        snapshot, rows = parse_hltv_standings(HLTV_STANDINGS)
        self.assertEqual(snapshot["date"], "2026_07_26")
        self.assertEqual(rows[0]["team"], "FaZe")
        self.assertEqual(rows[0]["points"], 1629)
        self.assertEqual(rows[0]["regional_rank"], 1)
        self.assertEqual(rows[0]["roster"][-1], "JBOEN")

    def test_hltv_detail_and_event_points(self):
        _, rows = parse_hltv_standings(HLTV_STANDINGS)
        detail = parse_hltv_team_detail(HLTV_DETAIL, rows[0])
        self.assertEqual(detail["global_rank"], 15)
        self.assertEqual(detail["h2h_total"], -79)
        self.assertEqual(detail["matches"][0]["date"], "2026-07-25")
        self.assertEqual(detail["matches"][0]["event"], "BLAST Bounty")
        self.assertEqual(len(detail["contributions"]), 3)
        result = simulate_roster(detail, ["frozen", "Twistzz", "Neityu"], ["a", "b", "c"])
        self.assertIsNone(result["indicative_score"])
        self.assertFalse(result["simulation_complete"])
        self.assertTrue(result["event_groups"])

    def test_unverified_history_never_claims_retained_points(self):
        _, rows = parse_hltv_standings(HLTV_STANDINGS)
        detail = parse_hltv_team_detail(HLTV_DETAIL, rows[0])
        result = simulate_roster(detail, ["Neityu"], ["siuhy"])
        self.assertTrue(all(row["status"] == "Unknown" for row in result["contribution_rows"]))
        self.assertTrue(all(group["status"] == "Unknown" for group in result["event_groups"]))

    def test_losing_negative_h2h_can_raise_indicative_score(self):
        detail = {
            "team": "Example",
            "roster": ["a", "b", "c", "d", "e"],
            "final_score": 470.0,
            "starting_score": 500.0,
            "h2h_total": -30.0,
            "factors": {"Bounty Offered": 100.0, "Head To Head": -30.0},
            "matches": [],
            "contributions": [
                {
                    "date": "2026-07-01",
                    "opponent": "",
                    "event": "Recent event",
                    "component": "Bounty Offered",
                    "points": 100.0,
                    "result": "",
                    "roster": ["a", "b", "c", "d", "e"],
                    "roster_verified": True,
                },
                {
                    "date": "2026-04-01",
                    "opponent": "Old opponent",
                    "event": "Old event",
                    "component": "Head To Head",
                    "points": -30.0,
                    "result": "L",
                    "roster": ["a", "b", "c", "y", "z"],
                    "roster_verified": True,
                },
            ],
            "prizes": [],
        }
        result = simulate_roster(detail, ["c"], ["x"])
        self.assertEqual(result["indicative_score"], 500.0)
        self.assertEqual(result["indicative_delta"], 30.0)
        h2h = next(
            row
            for row in result["component_breakdown"]
            if row["component"] == "Head To Head"
        )
        self.assertEqual(h2h["change"], 30.0)

    def test_hltv_result_dates_and_plain_match_lineup(self):
        links = parse_hltv_result_links(HLTV_RESULTS)
        self.assertEqual(links[0]["date"], "2026-07-03")
        _, rows = parse_hltv_standings(HLTV_STANDINGS)
        roster = parse_hltv_match_roster(HLTV_PLAIN_MATCH, rows[0])
        self.assertEqual(roster, ["karrigan", "broky", "Twistzz", "jcobbb", "frozen"])

    def test_recency_projection_and_timeline(self):
        self.assertEqual(recency_weight(date(2026, 7, 1), date(2026, 7, 31)), 1.0)
        self.assertEqual(recency_weight(date(2026, 1, 1), date(2026, 7, 3)), 0.0)
        _, rows = parse_hltv_standings(HLTV_STANDINGS)
        detail = parse_hltv_team_detail(HLTV_DETAIL, rows[0])
        current = project_vrs(detail, date(2026, 7, 26))
        future = project_vrs(detail, date(2026, 10, 26))
        self.assertEqual(current["baseline_score"], detail["final_score"])
        self.assertLess(future["baseline_score"], current["baseline_score"])
        timeline = build_vrs_timeline(detail, weeks=4)
        self.assertEqual(len(timeline["rows"]), 5)

    def test_hltv_invite_cards_and_cutoff(self):
        events = parse_hltv_invites(HLTV_INVITES, date(2026, 7, 26))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["name"], "EPL S24")
        self.assertEqual(events[0]["allocations"]["Global"], 12)
        self.assertEqual(events[1]["total_invites"], 29)
        prediction = parse_hltv_invite_ranking(HLTV_INVITE_RANKING, events[0])
        self.assertEqual(prediction["ranking_date"], "2026-08-03")
        self.assertEqual(prediction["cutoff"]["team"], "G2")
        self.assertEqual(prediction["first_out"]["team"], "FaZe")
        self.assertFalse(prediction["rows"][-1]["qualified"])

    def test_three_of_five_threshold(self):
        detail = parse_team_detail(DETAIL)
        result = simulate_roster(detail, ["Neityu", "Twistzz"], ["siuhy", "lauNX"])
        self.assertEqual(result["rows"][0]["overlap"], 3)
        self.assertEqual(result["rows"][0]["status"], "At risk")
        self.assertTrue(result["rows"][0]["eligible"])
        self.assertEqual(result["rows"][1]["overlap"], 3)

    def test_third_change_breaks_new_core(self):
        detail = parse_team_detail(DETAIL)
        result = simulate_roster(
            detail,
            ["jcobbb", "Neityu", "Twistzz"],
            ["siuhy", "lauNX", "Dawy"],
        )
        self.assertEqual(result["rows"][0]["overlap"], 2)
        self.assertFalse(result["rows"][0]["eligible"])


if __name__ == "__main__":
    unittest.main()
