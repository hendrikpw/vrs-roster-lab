import unittest

from vrs_data import parse_standings, parse_team_detail, simulate_roster


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


class ParserTests(unittest.TestCase):
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
