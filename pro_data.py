from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BO3_API_BASE = "https://api.bo3.gg/api/v1"
BO3_SITE_BASE = "https://bo3.gg"
USER_AGENT = "VRS-Roster-Lab/0.2"
CURRENT_ACTIVE_DUTY_MAP_POOL = [
    "Ancient",
    "Anubis",
    "Cache",
    "Dust2",
    "Inferno",
    "Mirage",
    "Nuke",
]
CURRENT_POOL_EFFECTIVE_FROM = date(2026, 7, 9)


class ProDataError(RuntimeError):
    pass


def _get_json(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{BO3_API_BASE}{endpoint}{query}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Origin": BO3_SITE_BASE,
            "Referer": f"{BO3_SITE_BASE}/",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProDataError(f"Could not load BO3.gg pro statistics: {exc}") from exc


def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _safe_div(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _map_name(value: str) -> str:
    value = value.removeprefix("de_")
    return "Dust2" if value == "dust2" else value.title()


def _best_result(results: list[dict[str, Any]], query: str, name_key: str) -> dict[str, Any]:
    if not results:
        raise ProDataError(f"No pro-play result was found for “{query}”.")
    query_key = _normal(query)
    exact = [
        row
        for row in results
        if _normal(str(row.get(name_key, ""))) == query_key
    ]
    candidates = exact or results
    return sorted(
        candidates,
        key=lambda row: (
            row.get("rank") is None,
            row.get("rank") or 99999,
            row.get("id") or 999999,
        ),
    )[0]


def search_players(query: str, limit: int = 8) -> list[dict[str, Any]]:
    payload = _get_json(
        "/filters/players",
        {
            "page[offset]": 0,
            "page[limit]": limit,
            "filter[discipline_id][eq]": 1,
            "with": "country",
            "search_text": query,
        },
    )
    return payload.get("results", []) if isinstance(payload, dict) else []


def search_teams(query: str, limit: int = 8) -> list[dict[str, Any]]:
    payload = _get_json(
        "/filters/teams",
        {
            "page[offset]": 0,
            "page[limit]": limit,
            "filter[teams.discipline_id][eq]": 1,
            "search_text": query,
        },
    )
    return payload.get("results", []) if isinstance(payload, dict) else []


def load_active_map_pool() -> list[str]:
    payload = _get_json(
        "/maps",
        {
            "page[offset]": 0,
            "page[limit]": 100,
            "filter[discipline_id][eq]": 1,
        },
    )
    rows = payload.get("results", []) if isinstance(payload, dict) else []
    active = sorted(
        {
            _map_name(str(row.get("map_name") or row.get("name") or ""))
            for row in rows
            if row.get("discipline_id") == 1 and row.get("map_pool") is True
        }
    )
    if len(active) != 7:
        raise ProDataError(
            f"The current CS2 Active Duty pool returned {len(active)} maps instead of seven."
        )
    return active


def resolve_player(query: str) -> dict[str, Any]:
    return _best_result(search_players(query), query, "nickname")


def resolve_team(query: str) -> dict[str, Any]:
    return _best_result(search_teams(query), query, "name")


def _style_indicators(stats: dict[str, Any]) -> dict[str, float | None]:
    rounds = float(stats.get("rounds_count") or 0)
    kills = float(stats.get("kills") or 0)
    deaths = float(stats.get("deaths") or 0)
    opening_total = float(stats.get("open_kills_sum") or 0) + float(
        stats.get("open_deaths_sum") or 0
    )
    return {
        "Opening involvement": _safe_div(opening_total, rounds),
        "Opening success": _safe_div(
            float(stats.get("open_kills_sum") or 0), opening_total
        ),
        "Headshot share": _safe_div(float(stats.get("headshots") or 0), kills),
        "Assist rate": _safe_div(float(stats.get("assists") or 0), rounds),
        "Trade-kill share": _safe_div(
            float(stats.get("trade_kills") or 0), kills
        ),
        "Survival rate": (
            1.0 - deaths / rounds if rounds and deaths <= rounds else None
        ),
    }


def load_player_profile(
    query: str, days: int = 180, reference_date: date | None = None
) -> dict[str, Any]:
    player = resolve_player(query)
    reference_date = reference_date or date.today()
    start_date = reference_date - timedelta(days=days)
    date_params = {
        "filter[start_date_to]": reference_date.isoformat(),
        "filter[start_date_from]": start_date.isoformat(),
    }
    begin_params = {
        "filter[begin_at_to]": reference_date.isoformat(),
        "filter[begin_at_from]": start_date.isoformat(),
    }
    slug = player["slug"]
    calls = [
        (f"/players/{slug}", {"prefer_locale": "en"}),
        (f"/players/{slug}/general_stats", date_params),
        (f"/players/{slug}/advanced_stats", begin_params),
        (f"/players/{slug}/map_stats", begin_params),
    ]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_get_json, endpoint, params) for endpoint, params in calls]
        profile, general, advanced_rows, map_rows = [future.result() for future in futures]

    general = general or {}
    advanced = advanced_rows[0] if isinstance(advanced_rows, list) and advanced_rows else {}
    map_rows = map_rows if isinstance(map_rows, list) else []
    rounds = float(advanced.get("rounds_count") or general.get("rounds_count") or 0)
    kills = float(advanced.get("kills") or general.get("kills_sum") or 0)
    deaths = float(advanced.get("deaths") or general.get("deaths_sum") or 0)
    rated_maps = [row for row in map_rows if row.get("avg_player_rating")]
    rating_weight = sum(float(row.get("maps_count") or 0) for row in rated_maps)
    rating = (
        sum(
            float(row["avg_player_rating"]) * float(row.get("maps_count") or 0)
            for row in rated_maps
        )
        / rating_weight
        if rating_weight
        else profile.get("six_month_avg_rating")
    )
    opening_total = float(advanced.get("open_kills_sum") or 0) + float(
        advanced.get("open_deaths_sum") or 0
    )
    metrics = {
        "BO3 rating": rating,
        "Maps": int(general.get("games_count") or 0),
        "Rounds": int(rounds),
        "K/D": _safe_div(kills, deaths),
        "KPR": _safe_div(kills, rounds),
        "DPR": _safe_div(deaths, rounds),
        "ADR": _safe_div(float(advanced.get("damage_deal") or general.get("damage_sum") or 0), rounds),
        "Headshot %": _safe_div(float(advanced.get("headshots") or 0), kills),
        "Opening duel win %": _safe_div(
            float(advanced.get("open_kills_sum") or 0), opening_total
        ),
        "Opening attempts / round": _safe_div(opening_total, rounds),
        "Assists / round": _safe_div(float(advanced.get("assists") or 0), rounds),
        "Trade kills / round": _safe_div(
            float(advanced.get("trade_kills") or 0), rounds
        ),
        "Clutches": int(advanced.get("clutches") or 0),
        "T round win %": _safe_div(
            float(advanced.get("t_round_wins_count") or 0),
            float(advanced.get("t_rounds_count") or 0),
        ),
        "CT round win %": _safe_div(
            float(advanced.get("ct_round_wins_count") or 0),
            float(advanced.get("ct_rounds_count") or 0),
        ),
    }
    maps = [
        {
            "map": _map_name(str(row.get("map_name", ""))),
            "maps": int(row.get("maps_count") or 0),
            "rating": float(row.get("avg_player_rating") or 0) or None,
            "kpr": float(row.get("avg_kills") or 0) or None,
            "adr": float(row.get("avg_damage") or 0) or None,
        }
        for row in map_rows
    ]
    return {
        "id": player["id"],
        "slug": slug,
        "nickname": profile.get("nickname") or player.get("nickname") or query,
        "name": " ".join(
            part
            for part in [profile.get("first_name"), profile.get("last_name")]
            if part
        ),
        "team": (profile.get("team") or {}).get("name") or "Unknown",
        "team_slug": (profile.get("team") or {}).get("slug") or "",
        "country": (profile.get("country") or {}).get("name") or "Unknown",
        "image_url": profile.get("image_url"),
        "period_days": days,
        "metrics": metrics,
        "maps": maps,
        "style": _style_indicators(advanced),
        "source_url": f"{BO3_SITE_BASE}/players/{slug}",
    }


def compare_players(current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    metric_order = [
        "BO3 rating",
        "Maps",
        "Rounds",
        "K/D",
        "KPR",
        "DPR",
        "ADR",
        "Headshot %",
        "Opening duel win %",
        "Opening attempts / round",
        "Assists / round",
        "Trade kills / round",
        "Clutches",
        "T round win %",
        "CT round win %",
    ]
    metrics = []
    lower_is_better = {"DPR"}
    for metric in metric_order:
        current_value = current["metrics"].get(metric)
        candidate_value = candidate["metrics"].get(metric)
        delta = (
            candidate_value - current_value
            if isinstance(current_value, (int, float))
            and isinstance(candidate_value, (int, float))
            else None
        )
        if metric in lower_is_better and delta is not None:
            advantage = -delta
        else:
            advantage = delta
        metrics.append(
            {
                "metric": metric,
                "current": current_value,
                "candidate": candidate_value,
                "delta": delta,
                "candidate_advantage": advantage,
            }
        )

    all_maps = sorted(
        {row["map"] for row in current["maps"]}
        | {row["map"] for row in candidate["maps"]}
    )
    current_maps = {row["map"]: row for row in current["maps"]}
    candidate_maps = {row["map"]: row for row in candidate["maps"]}
    maps = []
    for map_name in all_maps:
        left = current_maps.get(map_name, {})
        right = candidate_maps.get(map_name, {})
        maps.append(
            {
                "map": map_name,
                "current_maps": left.get("maps"),
                "current_rating": left.get("rating"),
                "candidate_maps": right.get("maps"),
                "candidate_rating": right.get("rating"),
                "rating_delta": (
                    right["rating"] - left["rating"]
                    if left.get("rating") is not None
                    and right.get("rating") is not None
                    else None
                ),
            }
        )

    style_pairs = [
        (current["style"].get(name), candidate["style"].get(name))
        for name in current["style"]
    ]
    distances = [
        min(abs(left - right) / max(0.05, (abs(left) + abs(right)) / 2), 1.0)
        for left, right in style_pairs
        if left is not None and right is not None
    ]
    style_similarity = 100 * (1 - sum(distances) / len(distances)) if distances else None

    # Statistical role fit measures how closely the candidate mirrors the outgoing
    # player's observed involvement. Performance values such as rating and ADR stay
    # separate so a stronger player with a different job is not mislabeled as a
    # like-for-like replacement.
    role_dimensions = {
        "Opening involvement": {"weight": 0.30, "tolerance": 0.08},
        "Trade-kill share": {"weight": 0.20, "tolerance": 0.25},
        "Assist rate": {"weight": 0.15, "tolerance": 0.07},
        "Survival rate": {"weight": 0.15, "tolerance": 0.18},
        "Headshot share": {"weight": 0.10, "tolerance": 0.35},
        "Opening success": {"weight": 0.10, "tolerance": 0.20},
    }
    role_breakdown = []
    available_weight = 0.0
    weighted_fit = 0.0
    for indicator, config in role_dimensions.items():
        current_value = current["style"].get(indicator)
        candidate_value = candidate["style"].get(indicator)
        if current_value is None or candidate_value is None:
            continue
        difference = candidate_value - current_value
        similarity = max(
            0.0,
            1.0 - abs(difference) / config["tolerance"],
        )
        available_weight += config["weight"]
        weighted_fit += similarity * config["weight"]
        role_breakdown.append(
            {
                "indicator": indicator,
                "current": current_value,
                "candidate": candidate_value,
                "difference": difference,
                "weight": config["weight"],
                "similarity": similarity,
            }
        )

    role_fit_score = (
        100 * weighted_fit / available_weight if available_weight else None
    )
    if role_fit_score is None:
        role_fit_label = "Unavailable"
    elif role_fit_score >= 85:
        role_fit_label = "Like-for-like"
    elif role_fit_score >= 70:
        role_fit_label = "Similar with adjustments"
    elif role_fit_score >= 55:
        role_fit_label = "Noticeable role change"
    else:
        role_fit_label = "Major role change"

    current_rounds = float(current["metrics"].get("Rounds") or 0)
    candidate_rounds = float(candidate["metrics"].get("Rounds") or 0)
    current_map_count = float(current["metrics"].get("Maps") or 0)
    candidate_map_count = float(candidate["metrics"].get("Maps") or 0)
    shared_rounds = min(current_rounds, candidate_rounds)
    shared_maps = min(current_map_count, candidate_map_count)
    metric_coverage = available_weight / sum(
        config["weight"] for config in role_dimensions.values()
    )
    confidence_score = 100 * (
        0.55 * min(shared_rounds / 600, 1.0)
        + 0.25 * min(shared_maps / 25, 1.0)
        + 0.20 * metric_coverage
    )
    if confidence_score >= 80:
        confidence_label = "High"
    elif confidence_score >= 50:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"

    return {
        "metrics": metrics,
        "maps": maps,
        "style_similarity": style_similarity,
        "role_fit": {
            "score": role_fit_score,
            "label": role_fit_label,
            "breakdown": role_breakdown,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "compared_metrics": len(role_breakdown),
            "total_metrics": len(role_dimensions),
            "minimum_rounds": int(shared_rounds),
            "minimum_maps": int(shared_maps),
        },
        "unavailable_splits": ["LAN / online", "Top 10", "Top 20", "Top 30"],
    }


def load_team_map_data(
    query: str,
    days: int = 180,
    reference_date: date | None = None,
    start_date: date | None = None,
) -> dict[str, Any]:
    team = resolve_team(query)
    reference_date = reference_date or date.today()
    start_date = start_date or reference_date - timedelta(days=days)
    payload = _get_json(
        "/matches",
        {
            "scope": "widget-map-pool",
            "page[offset]": 0,
            "page[limit]": 100,
            "sort": "-start_date",
            "filter[matches.status][in]": "finished",
            "filter[matches.team_ids][overlap]": team["id"],
            "filter[matches.start_date][lt]": (
                reference_date + timedelta(days=1)
            ).isoformat(),
            "filter[matches.start_date][gt]": start_date.isoformat(),
            "filter[matches.discipline_id][eq]": 1,
            "with": "teams,tournament,games,match_maps",
        },
    )
    matches = payload.get("results", []) if isinstance(payload, dict) else []
    map_stats: dict[str, dict[str, Any]] = {}
    veto_counts: dict[str, dict[str, int]] = {}
    opponents: list[str] = []
    match_wins = 0
    match_losses = 0

    for match in matches:
        opponent = match.get("team2") if match.get("team1", {}).get("id") == team["id"] else match.get("team1")
        if opponent and opponent.get("name"):
            opponents.append(opponent["name"])
        team_game_wins = 0
        opponent_game_wins = 0
        for game in match.get("games") or []:
            map_name = _map_name(str(game.get("map_name", "")))
            row = map_stats.setdefault(
                map_name,
                {
                    "map": map_name,
                    "played": 0,
                    "wins": 0,
                    "losses": 0,
                    "rounds_won": 0,
                    "rounds_lost": 0,
                },
            )
            winner_id = (
                ((game.get("winner_team_clan") or {}).get("team") or {}).get("id")
            )
            team_won = winner_id == team["id"]
            row["played"] += 1
            row["wins" if team_won else "losses"] += 1
            row["rounds_won"] += int(
                (
                    game.get("winner_clan_score")
                    if team_won
                    else game.get("loser_clan_score")
                )
                or 0
            )
            row["rounds_lost"] += int(
                (
                    game.get("loser_clan_score")
                    if team_won
                    else game.get("winner_clan_score")
                )
                or 0
            )
            if team_won:
                team_game_wins += 1
            else:
                opponent_game_wins += 1
        if team_game_wins > opponent_game_wins:
            match_wins += 1
        elif opponent_game_wins > team_game_wins:
            match_losses += 1

        for choice in match.get("match_maps") or []:
            maps = choice.get("maps") or {}
            map_name = _map_name(str(maps.get("map_name") or maps.get("name") or ""))
            if not map_name:
                continue
            action = {1: "picks", 2: "bans", 3: "deciders"}.get(
                choice.get("choice_type")
            )
            if not action:
                continue
            counts = veto_counts.setdefault(
                map_name, {"picks": 0, "bans": 0, "deciders": 0}
            )
            if action == "deciders" or choice.get("team_id") == team["id"]:
                counts[action] += 1

    for row in map_stats.values():
        row["win_rate"] = _safe_div(row["wins"], row["played"])
        row["round_diff"] = row["rounds_won"] - row["rounds_lost"]
        row.update(veto_counts.get(row["map"], {"picks": 0, "bans": 0, "deciders": 0}))
    for map_name, counts in veto_counts.items():
        if map_name not in map_stats:
            map_stats[map_name] = {
                "map": map_name,
                "played": 0,
                "wins": 0,
                "losses": 0,
                "rounds_won": 0,
                "rounds_lost": 0,
                "win_rate": None,
                "round_diff": 0,
                **counts,
            }
    matches_count = match_wins + match_losses
    return {
        "id": team["id"],
        "slug": team["slug"],
        "name": team["name"],
        "rank": team.get("rank"),
        "period_days": days,
        "period_start": start_date.isoformat(),
        "period_end": reference_date.isoformat(),
        "matches": matches_count,
        "match_wins": match_wins,
        "match_losses": match_losses,
        "match_win_rate": _safe_div(match_wins, matches_count),
        "maps": sorted(map_stats.values(), key=lambda row: row["map"]),
        "opponents": opponents,
        "source_url": f"{BO3_SITE_BASE}/teams/{team['slug']}",
    }


def _smoothed_win_rate(row: dict[str, Any] | None) -> float:
    row = row or {}
    return (float(row.get("wins") or 0) + 2.0) / (
        float(row.get("played") or 0) + 4.0
    )


def _series_probability(map_probabilities: list[float]) -> float:
    needed = len(map_probabilities) // 2 + 1
    distribution = [1.0] + [0.0] * len(map_probabilities)
    for probability in map_probabilities:
        updated = [0.0] * len(distribution)
        for wins, chance in enumerate(distribution):
            updated[wins] += chance * (1 - probability)
            if wins + 1 < len(updated):
                updated[wins + 1] += chance * probability
        distribution = updated
    return sum(distribution[needed:])


def predict_veto(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    best_of: int = 3,
    active_map_pool: list[str] | None = None,
) -> dict[str, Any]:
    if best_of not in {3, 5}:
        raise ValueError("Only BO3 and BO5 vetoes are supported.")
    a_maps = {row["map"]: row for row in team_a["maps"]}
    b_maps = {row["map"]: row for row in team_b["maps"]}
    pool = list(active_map_pool or CURRENT_ACTIVE_DUTY_MAP_POOL)
    if len(pool) != 7 or len(set(pool)) != 7:
        raise ValueError("The veto predictor requires exactly seven unique active maps.")

    overall_a = (team_a["match_wins"] + 2) / (team_a["matches"] + 4)
    overall_b = (team_b["match_wins"] + 2) / (team_b["matches"] + 4)

    def map_probability(map_name: str) -> float:
        map_edge = (
            _smoothed_win_rate(a_maps.get(map_name))
            + (1 - _smoothed_win_rate(b_maps.get(map_name)))
        ) / 2
        overall_edge = (overall_a + (1 - overall_b)) / 2
        return min(0.9, max(0.1, 0.75 * map_edge + 0.25 * overall_edge))

    def ban(team_maps: dict[str, dict[str, Any]], available: list[str]) -> str:
        return max(
            available,
            key=lambda name: (
                team_maps.get(name, {}).get("bans", 0),
                -_smoothed_win_rate(team_maps.get(name)),
                -team_maps.get(name, {}).get("played", 0),
            ),
        )

    def pick(team_maps: dict[str, dict[str, Any]], available: list[str]) -> str:
        return max(
            available,
            key=lambda name: (
                team_maps.get(name, {}).get("picks", 0),
                _smoothed_win_rate(team_maps.get(name)),
                team_maps.get(name, {}).get("played", 0),
            ),
        )

    available = list(pool)
    sequence: list[dict[str, Any]] = []
    ban_a = ban(a_maps, available)
    available.remove(ban_a)
    sequence.append({"step": 1, "team": team_a["name"], "action": "Ban", "map": ban_a})
    ban_b = ban(b_maps, available)
    available.remove(ban_b)
    sequence.append({"step": 2, "team": team_b["name"], "action": "Ban", "map": ban_b})

    played_maps: list[str] = []
    if best_of == 3:
        pick_a = pick(a_maps, available)
        available.remove(pick_a)
        played_maps.append(pick_a)
        sequence.append({"step": 3, "team": team_a["name"], "action": "Pick", "map": pick_a})
        pick_b = pick(b_maps, available)
        available.remove(pick_b)
        played_maps.append(pick_b)
        sequence.append({"step": 4, "team": team_b["name"], "action": "Pick", "map": pick_b})
        second_ban_a = ban(a_maps, available)
        available.remove(second_ban_a)
        sequence.append({"step": 5, "team": team_a["name"], "action": "Ban", "map": second_ban_a})
        second_ban_b = ban(b_maps, available)
        available.remove(second_ban_b)
        sequence.append({"step": 6, "team": team_b["name"], "action": "Ban", "map": second_ban_b})
        decider = available[0]
        played_maps.append(decider)
        sequence.append({"step": 7, "team": "—", "action": "Decider", "map": decider})
    else:
        turn = 0
        while available:
            owner = team_a if turn % 2 == 0 else team_b
            owner_maps = a_maps if turn % 2 == 0 else b_maps
            map_name = pick(owner_maps, available)
            available.remove(map_name)
            played_maps.append(map_name)
            action = "Decider" if not available else "Pick"
            sequence.append(
                {
                    "step": len(sequence) + 1,
                    "team": "—" if action == "Decider" else owner["name"],
                    "action": action,
                    "map": map_name,
                }
            )
            turn += 1

    comparisons = []
    for map_name in pool:
        left = a_maps.get(map_name, {})
        right = b_maps.get(map_name, {})
        comparisons.append(
            {
                "map": map_name,
                "team_a_played": left.get("played", 0),
                "team_a_win_rate": left.get("win_rate"),
                "team_a_picks": left.get("picks", 0),
                "team_a_bans": left.get("bans", 0),
                "team_b_played": right.get("played", 0),
                "team_b_win_rate": right.get("win_rate"),
                "team_b_picks": right.get("picks", 0),
                "team_b_bans": right.get("bans", 0),
                "team_a_probability": map_probability(map_name),
                "selected": map_name in played_maps,
            }
        )
    selected_probabilities = [map_probability(map_name) for map_name in played_maps]
    return {
        "best_of": best_of,
        "active_map_pool": pool,
        "sequence": sequence,
        "maps": comparisons,
        "played_maps": played_maps,
        "team_a_series_probability": _series_probability(selected_probabilities),
        "team_b_series_probability": 1 - _series_probability(selected_probabilities),
    }


def opponent_rank_summary(
    team_data: dict[str, Any], standings: list[dict[str, Any]]
) -> dict[str, Any]:
    ranks = {_normal(row["team"]): row["rank"] for row in standings}
    matched = [
        ranks[_normal(opponent)]
        for opponent in team_data["opponents"]
        if _normal(opponent) in ranks
    ]
    return {
        "average_rank": sum(matched) / len(matched) if matched else None,
        "matched": len(matched),
        "total": len(team_data["opponents"]),
    }
