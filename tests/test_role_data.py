import unittest
from unittest.mock import patch

from role_data import (
    extract_rdy_overall_role,
    load_rdy_role_profile,
    load_rdy_role_profiles,
)


class RoleDataTests(unittest.TestCase):
    def test_extracts_rdy_overall_role(self):
        page = """
        <div>lauNX (Fut, Star Rifler, 59)</div>
        <div>Spinx (Mouz, Star Rifler, 58)</div>
        """
        result = extract_rdy_overall_role(page, "lauNX")
        self.assertEqual(result["team"], "Fut")
        self.assertEqual(result["overall_role"], "Star Rifler")
        self.assertEqual(result["role_score"], 59)

    def test_missing_player_stays_explicit(self):
        with patch("role_data._fetch_rdy_page", return_value="<div>other</div>"):
            result = load_rdy_role_profile("unknown")
        self.assertIsNone(result["overall_role"])
        self.assertEqual(result["status"], "No structured role found")
        self.assertEqual(result["position_coverage"], 0)

    def test_batch_fetches_source_once(self):
        page = "jcobbb (FaZe, Support, 44) lauNX (Fut, Star Rifler, 59)"
        with patch("role_data._fetch_rdy_page", return_value=page) as fetch:
            current, candidate = load_rdy_role_profiles(("jcobbb", "lauNX"))
        fetch.assert_called_once()
        self.assertEqual(current["overall_role"], "Support")
        self.assertEqual(candidate["overall_role"], "Star Rifler")


if __name__ == "__main__":
    unittest.main()
