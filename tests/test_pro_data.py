import unittest
from datetime import date
from unittest.mock import patch

from pro_data import (
    compare_players,
    load_active_map_pool,
    load_player_profile,
    load_team_map_data,
    opponent_rank_summary,
    predict_veto,
)


def team_fixture(name, strength_shift=0):
    maps = []
    names = ["Ancient", "Anubis", "Cache", "Dust2", "Inferno", "Mirage", "Nuke"]
    for index, map_name in enumerate(names):
        played = 8 + index
        wins = max(0, min(played, 4 + index // 2 + strength_shift))
        maps.append(
            {
                "map": map_name,
                "played": played,
                "wins": wins,
                "losses": played - wins,
                "rounds_won": wins * 13,
                "rounds_lost": (played - wins) * 13,
                "round_diff": (2 * wins - played) * 13,
                "win_rate": wins / played,
                "picks": index % 3,
                "bans": (6 - index) % 4,
                "deciders": 0,
            }
        )
    return {
        "id": 1 if name == "Alpha" else 2,
        "slug": name.casefold(),
        "name": name,
        "matches": 20,
        "match_wins": 11 + strength_shift,
        "match_losses": 9 - strength_shift,
        "match_win_rate": (11 + strength_shift) / 20,
        "maps": maps,
        "opponents": ["FaZe", "Spirit", "Unranked"],
    }


class ProDataTests(unittest.TestCase):
    def test_active_map_pool_uses_current_api_flags(self):
        names = ["Ancient", "Anubis", "Cache", "Dust2", "Inferno", "Mirage", "Nuke"]
        payload = {
            "results": [
                {
                    "name": name,
                    "map_name": f"de_{name.casefold()}",
                    "discipline_id": 1,
                    "map_pool": True,
                }
                for name in names
            ]
            + [
                {
                    "name": "Overpass",
                    "map_name": "de_overpass",
                    "discipline_id": 1,
                    "map_pool": False,
                }
            ]
        }
        with patch("pro_data._get_json", return_value=payload):
            pool = load_active_map_pool()
        self.assertIn("Inferno", pool)
        self.assertNotIn("Overpass", pool)
        self.assertEqual(len(pool), 7)

    def test_player_profile_metrics(self):
        profile = {
            "nickname": "frozen",
            "first_name": "David",
            "last_name": "C",
            "team": {"name": "FaZe", "slug": "faze"},
            "country": {"name": "Slovakia"},
            "image_url": None,
        }
        general = {
            "games_count": 10,
            "rounds_count": 200,
            "kills_sum": 150,
            "deaths_sum": 120,
            "damage_sum": 16000,
        }
        advanced = [
            {
                "rounds_count": 200,
                "kills": 150,
                "deaths": 120,
                "damage_deal": 16000,
                "headshots": 75,
                "open_kills_sum": 25,
                "open_deaths_sum": 20,
                "assists": 50,
                "trade_kills": 30,
                "clutches": 3,
                "t_rounds_count": 100,
                "t_round_wins_count": 52,
                "ct_rounds_count": 100,
                "ct_round_wins_count": 55,
            }
        ]
        map_stats = [
            {
                "map_name": "de_nuke",
                "maps_count": 10,
                "avg_player_rating": 6.2,
                "avg_kills": 0.75,
                "avg_damage": 80,
            }
        ]

        def fake_get(endpoint, params=None):
            if endpoint.endswith("/general_stats"):
                return general
            if endpoint.endswith("/advanced_stats"):
                return advanced
            if endpoint.endswith("/map_stats"):
                return map_stats
            return profile

        with patch(
            "pro_data.resolve_player",
            return_value={"id": 1, "slug": "frozen", "nickname": "frozen"},
        ), patch("pro_data._get_json", side_effect=fake_get):
            result = load_player_profile("frozen", 90, date(2026, 7, 26))
        self.assertEqual(result["metrics"]["BO3 rating"], 6.2)
        self.assertEqual(result["metrics"]["ADR"], 80)
        self.assertEqual(result["metrics"]["K/D"], 1.25)
        self.assertEqual(result["maps"][0]["map"], "Nuke")

    def test_player_comparison_and_map_delta(self):
        current = {
            "metrics": {
                "BO3 rating": 6.0,
                "Maps": 10,
                "Rounds": 200,
                "K/D": 1.0,
                "KPR": 0.7,
                "DPR": 0.7,
                "ADR": 75,
                "Headshot %": 0.5,
                "Opening duel win %": 0.5,
                "Opening attempts / round": 0.2,
                "Assists / round": 0.2,
                "Trade kills / round": 0.1,
                "Clutches": 2,
                "T round win %": 0.5,
                "CT round win %": 0.5,
            },
            "maps": [{"map": "Nuke", "maps": 5, "rating": 6.0}],
            "style": {"Opening involvement": 0.2, "Assist rate": 0.2},
        }
        candidate = {
            "metrics": {**current["metrics"], "BO3 rating": 6.4, "DPR": 0.65},
            "maps": [{"map": "Nuke", "maps": 6, "rating": 6.5}],
            "style": {"Opening involvement": 0.21, "Assist rate": 0.19},
        }
        result = compare_players(current, candidate)
        rating = next(row for row in result["metrics"] if row["metric"] == "BO3 rating")
        self.assertAlmostEqual(rating["delta"], 0.4)
        self.assertAlmostEqual(result["maps"][0]["rating_delta"], 0.5)
        self.assertGreater(result["style_similarity"], 90)
        self.assertGreater(result["role_fit"]["score"], 85)
        self.assertEqual(result["role_fit"]["label"], "Like-for-like")
        self.assertEqual(result["role_fit"]["compared_metrics"], 2)
        self.assertEqual(result["role_fit"]["total_metrics"], 6)

    def test_team_match_and_veto_parsing(self):
        payload = {
            "results": [
                {
                    "team1": {"id": 1, "name": "Alpha"},
                    "team2": {"id": 2, "name": "Beta"},
                    "games": [
                        {
                            "map_name": "de_nuke",
                            "winner_clan_score": 13,
                            "loser_clan_score": 8,
                            "winner_team_clan": {"team": {"id": 1}},
                        }
                    ],
                    "match_maps": [
                        {
                            "choice_type": 2,
                            "team_id": 1,
                            "maps": {"map_name": "de_inferno"},
                        },
                        {
                            "choice_type": 1,
                            "team_id": 1,
                            "maps": {"map_name": "de_nuke"},
                        },
                        {
                            "choice_type": 3,
                            "maps": {"map_name": "de_ancient"},
                        },
                    ],
                }
            ]
        }
        with patch(
            "pro_data.resolve_team",
            return_value={"id": 1, "slug": "alpha", "name": "Alpha", "rank": 1},
        ), patch("pro_data._get_json", return_value=payload):
            result = load_team_map_data("Alpha", 90, date(2026, 7, 26))
        nuke = next(row for row in result["maps"] if row["map"] == "Nuke")
        inferno = next(row for row in result["maps"] if row["map"] == "Inferno")
        self.assertEqual(nuke["wins"], 1)
        self.assertEqual(nuke["picks"], 1)
        self.assertEqual(inferno["bans"], 1)
        self.assertEqual(result["match_win_rate"], 1)

    def test_veto_prediction_is_complete(self):
        alpha = team_fixture("Alpha", 1)
        beta = team_fixture("Beta", -1)
        alpha["maps"].append(
            {
                "map": "Overpass",
                "played": 30,
                "wins": 0,
                "losses": 30,
                "win_rate": 0,
                "picks": 0,
                "bans": 30,
                "deciders": 0,
            }
        )
        prediction = predict_veto(alpha, beta, 3)
        self.assertEqual(len(prediction["sequence"]), 7)
        self.assertEqual(len(prediction["played_maps"]), 3)
        self.assertEqual(len(set(row["map"] for row in prediction["sequence"])), 7)
        self.assertIn("Inferno", prediction["active_map_pool"])
        self.assertNotIn("Overpass", prediction["active_map_pool"])
        self.assertAlmostEqual(
            prediction["team_a_series_probability"]
            + prediction["team_b_series_probability"],
            1.0,
        )
        bo5 = predict_veto(alpha, beta, 5)
        self.assertEqual(len(bo5["sequence"]), 7)
        self.assertEqual(len(bo5["played_maps"]), 5)
        self.assertEqual(bo5["sequence"][-1]["action"], "Decider")

    def test_opponent_rank_coverage(self):
        summary = opponent_rank_summary(
            team_fixture("Alpha"),
            [{"team": "FaZe", "rank": 15}, {"team": "Spirit", "rank": 1}],
        )
        self.assertEqual(summary["average_rank"], 8)
        self.assertEqual(summary["matched"], 2)
        self.assertEqual(summary["total"], 3)


if __name__ == "__main__":
    unittest.main()
