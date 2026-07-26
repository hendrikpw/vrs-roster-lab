from __future__ import annotations

import json
import re
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = "ValveSoftware/counter-strike_regional_standings"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/"
API_BASE = f"https://api.github.com/repos/{REPO}/contents/"
USER_AGENT = "VRS-Roster-Lab/0.1"


class VRSDataError(RuntimeError):
    pass


def _get_text(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise VRSDataError(f"Could not load Valve ranking data: {exc}") from exc


def _get_json(url: str, timeout: int = 20) -> Any:
    return json.loads(_get_text(url, timeout=timeout))


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _float(value: str, default: float = 0.0) -> float:
    cleaned = value.replace(",", "").replace("$", "").strip()
    if cleaned in {"", "-"}:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def _adjusted_value(value: str) -> float:
    match = re.search(r"\((-?\d+(?:\.\d+)?)\)", value)
    return _float(match.group(1)) if match else 0.0


def _field(markdown: str, label: str, default: str = "") -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)(?:<br\s*/?>)?$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else default


def discover_latest_snapshot(reference_date: date | None = None) -> dict[str, str]:
    reference_date = reference_date or date.today()
    candidates: list[tuple[str, str]] = []
    for year in (reference_date.year, reference_date.year - 1):
        try:
            entries = _get_json(f"{API_BASE}live/{year}")
        except VRSDataError:
            continue
        for entry in entries:
            name = entry.get("name", "")
            match = re.fullmatch(r"standings_global_(\d{4}_\d{2}_\d{2})\.md", name)
            if match:
                candidates.append((match.group(1), f"live/{year}/{name}"))
    if not candidates:
        raise VRSDataError("No current global standings snapshot was found.")
    snapshot_date, path = max(candidates, key=lambda item: item[0])
    return {"date": snapshot_date, "path": path}


def parse_standings(markdown: str, source_path: str) -> list[dict[str, Any]]:
    snapshot_match = re.search(r"standings_global_(\d{4}_\d{2}_\d{2})\.md", source_path)
    snapshot_date = snapshot_match.group(1) if snapshot_match else ""
    year = snapshot_date[:4]
    rows: list[dict[str, Any]] = []

    for line in markdown.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        link = re.search(r"\(([^)]+)\)", cells[4])
        detail_path = link.group(1) if link else ""
        detail_repo_path = f"live/{year}/{detail_path}" if detail_path else ""
        rows.append(
            {
                "rank": int(cells[0]),
                "points": int(_float(cells[1])),
                "team": cells[2],
                "roster": [player.strip() for player in cells[3].split(",") if player.strip()],
                "snapshot_date": snapshot_date,
                "detail_path": detail_repo_path,
                "detail_url": f"{RAW_BASE}{detail_repo_path}" if detail_repo_path else "",
            }
        )
    if not rows:
        raise VRSDataError("The standings snapshot did not contain any ranking rows.")
    return rows


def load_latest_standings() -> tuple[dict[str, str], list[dict[str, Any]]]:
    snapshot = discover_latest_snapshot()
    markdown = _get_text(f"{RAW_BASE}{snapshot['path']}")
    return snapshot, parse_standings(markdown, snapshot["path"])


def parse_team_detail(markdown: str) -> dict[str, Any]:
    score_match = re.search(
        r"Final Rank Value \(([-\d.]+)\) = Starting Rank Value \(([-\d.]+)\) "
        r"\+ Head To Head Adjustments \(([-\d.]+)\)",
        markdown,
    )
    factor_names = ("Bounty Offered", "Bounty Collected", "Opponent Network", "LAN Wins")
    factors = {name: _float(_field(markdown, f"- {name}")) for name in factor_names}
    if not any(factors.values()):
        factors = {}
        for name in factor_names:
            match = re.search(rf"-\s*{re.escape(name)}:\s*([-\d.]+)", markdown)
            factors[name] = _float(match.group(1)) if match else 0.0

    matches: list[dict[str, Any]] = []
    prizes: list[dict[str, Any]] = []
    table = ""
    for line in markdown.splitlines():
        if line.startswith("| Match Played"):
            table = "matches"
            continue
        if line.startswith("| Event Date"):
            table = "prizes"
            continue
        if not line.lstrip().startswith("|") or line.startswith("| -"):
            continue
        cells = _cells(line)
        if table == "matches" and len(cells) == 12 and cells[0].isdigit():
            roster = [player.strip() for player in cells[11].split(",") if player.strip()]
            matches.append(
                {
                    "match_number": int(cells[0]),
                    "match_id": int(cells[1]),
                    "date": cells[2],
                    "opponent": cells[3],
                    "result": cells[4],
                    "age_weight": _float(cells[5]),
                    "event_weight": _float(cells[6]),
                    "bounty_adjusted": _adjusted_value(cells[7]),
                    "network_adjusted": _adjusted_value(cells[8]),
                    "lan_adjusted": _adjusted_value(cells[9]),
                    "h2h": _float(cells[10]),
                    "roster": roster,
                }
            )
        elif table == "prizes" and len(cells) == 4 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            prizes.append(
                {
                    "date": cells[0],
                    "age_weight": _float(cells[1]),
                    "prize": _float(cells[2]),
                    "scaled_prize": _float(cells[3]),
                }
            )

    roster = [player.strip() for player in _field(markdown, "Roster").split(",") if player.strip()]
    final_score = _float(_field(markdown, "Final Rank Value"))
    starting_score = score_match and _float(score_match.group(2)) or final_score
    h2h_total = score_match and _float(score_match.group(3)) or sum(row["h2h"] for row in matches)

    return {
        "team": _field(markdown, "Team Name"),
        "roster": roster,
        "global_rank": int(_float(_field(markdown, "Global Rank"))),
        "region": _field(markdown, "Region"),
        "regional_rank": int(_float(_field(markdown, "Regional Rank"))),
        "final_score": final_score,
        "starting_score": starting_score,
        "h2h_total": h2h_total,
        "factors": factors,
        "matches": matches,
        "prizes": prizes,
    }


def load_team_detail(detail_url: str) -> dict[str, Any]:
    if not detail_url.startswith(RAW_BASE):
        raise VRSDataError("Unexpected detail URL.")
    return parse_team_detail(_get_text(detail_url))


def normalize_player(name: str) -> str:
    return re.sub(r"\s+", "", name).casefold()


def simulate_roster(
    detail: dict[str, Any],
    leaving: list[str],
    replacements: list[str] | None = None,
) -> dict[str, Any]:
    replacements = [name.strip() for name in (replacements or []) if name.strip()]
    leaving_keys = {normalize_player(name) for name in leaving}
    retained = [name for name in detail["roster"] if normalize_player(name) not in leaving_keys]
    simulated_roster = retained + replacements
    simulated_keys = {normalize_player(name) for name in simulated_roster}

    rows: list[dict[str, Any]] = []
    total_factor_support = 0.0
    retained_factor_support = 0.0
    retained_h2h = 0.0

    for match in detail["matches"]:
        historical_keys = {normalize_player(name) for name in match["roster"]}
        overlap = len(simulated_keys & historical_keys)
        eligible = overlap >= 3
        status = "Retained" if overlap >= 4 else "At risk" if overlap == 3 else "Lost"
        factor_support = (
            match["bounty_adjusted"] + match["network_adjusted"] + match["lan_adjusted"]
        )
        total_factor_support += factor_support
        if eligible:
            retained_factor_support += factor_support
            retained_h2h += match["h2h"]
        rows.append({**match, "overlap": overlap, "eligible": eligible, "status": status})

    all_eligible = bool(rows) and all(row["eligible"] for row in rows)
    factor_ratio = (
        retained_factor_support / total_factor_support if total_factor_support > 0 else 1.0
    )
    if all_eligible:
        indicative_score = detail["final_score"]
    else:
        indicative_start = 400 + max(0.0, detail["starting_score"] - 400) * factor_ratio
        indicative_score = max(400.0, indicative_start + retained_h2h)

    core_groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = ", ".join(row["roster"])
        group = core_groups.setdefault(
            key,
            {
                "roster": key,
                "matches": 0,
                "overlap": row["overlap"],
                "status": row["status"],
                "eligible": row["eligible"],
            },
        )
        group["matches"] += 1

    return {
        "simulated_roster": simulated_roster,
        "retained_players": retained,
        "rows": rows,
        "core_groups": list(core_groups.values()),
        "retained_matches": sum(row["eligible"] for row in rows),
        "lost_matches": sum(not row["eligible"] for row in rows),
        "fragile_matches": sum(row["status"] == "At risk" for row in rows),
        "factor_ratio": factor_ratio,
        "indicative_score": indicative_score,
        "indicative_delta": indicative_score - detail["final_score"],
    }


def fallback_data() -> tuple[dict[str, str], list[dict[str, Any]], dict[str, Any]]:
    snapshot = {"date": "2026_07_06", "path": "offline-demo"}
    standings = [
        {
            "rank": 23,
            "points": 1404,
            "team": "FaZe",
            "roster": ["broky", "frozen", "jcobbb", "Neityu", "Twistzz"],
            "snapshot_date": snapshot["date"],
            "detail_path": "",
            "detail_url": "",
        }
    ]
    detail = {
        "team": "FaZe",
        "roster": standings[0]["roster"],
        "global_rank": 23,
        "region": "Europe",
        "regional_rank": 16,
        "final_score": 1404.5,
        "starting_score": 1440.8,
        "h2h_total": -36.4,
        "factors": {
            "Bounty Offered": 0.663,
            "Bounty Collected": 0.534,
            "Opponent Network": 0.229,
            "LAN Wins": 0.783,
        },
        "matches": [
            {
                "match_number": 37,
                "match_id": 681,
                "date": "2026-05-30",
                "opponent": "Ninjas in Pyjamas",
                "result": "L",
                "age_weight": 0.953,
                "event_weight": 0.0,
                "bounty_adjusted": 0.0,
                "network_adjusted": 0.0,
                "lan_adjusted": 0.0,
                "h2h": -18.57,
                "roster": standings[0]["roster"],
            },
            {
                "match_number": 25,
                "match_id": 2438,
                "date": "2026-04-06",
                "opponent": "Inner Circle",
                "result": "L",
                "age_weight": 0.593,
                "event_weight": 0.0,
                "bounty_adjusted": 0.0,
                "network_adjusted": 0.0,
                "lan_adjusted": 0.0,
                "h2h": -8.88,
                "roster": ["broky", "frozen", "jcobbb", "karrigan", "Twistzz"],
            },
        ],
        "prizes": [],
    }
    return snapshot, standings, detail
