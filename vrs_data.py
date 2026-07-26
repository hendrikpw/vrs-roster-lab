from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = "ValveSoftware/counter-strike_regional_standings"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main/"
API_BASE = f"https://api.github.com/repos/{REPO}/contents/"
USER_AGENT = "VRS-Roster-Lab/0.1"
HLTV_LIVE_URL = "https://www.hltv.org/valve-ranking/teams"
JINA_BASE = "https://r.jina.ai/"
REGION_NAMES = {"EU": "Europe", "AM": "Americas", "AS": "Asia"}


class VRSDataError(RuntimeError):
    pass


def _get_text(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise VRSDataError(f"Could not load ranking data: {exc}") from exc


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


def _clean_markdown_label(value: str) -> str:
    value = re.sub(r"!\[[^\]]*]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def _field(markdown: str, label: str, default: str = "") -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)(?:<br\s*/?>)?$", markdown, re.MULTILINE)
    return _clean_markdown_label(match.group(1)) if match else default


def _iso_hltv_date(value: str) -> str:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%y").date().isoformat()
    except ValueError:
        return value.strip()


def parse_hltv_standings(markdown: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    date_match = re.search(
        r"Valve global ranking on ([A-Za-z]+) (\d+)(?:st|nd|rd|th), (\d{4})",
        markdown,
    )
    if not date_match:
        raise VRSDataError("HLTV's live VRS date could not be read.")
    snapshot_date = datetime.strptime(
        f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}", "%B %d %Y"
    ).date().strftime("%Y_%m_%d")

    markers = list(re.finditer(r"^#(\d+)!\[Image", markdown, re.MULTILINE))
    rows: list[dict[str, Any]] = []
    regional_counts: dict[str, int] = {}
    for index, marker in enumerate(markers):
        block_end = markers[index + 1].start() if index + 1 < len(markers) else len(markdown)
        block = markdown[marker.start():block_end]
        team_match = re.search(
            r"^(.+?)\((\d+) Valve points\)(EU|AM|AS)$", block, re.MULTILINE
        )
        detail_match = re.search(r"\[Ranking details]\((https://www\.hltv\.org/[^)]+)\)", block)
        team_url_match = re.search(r"\[HLTV Team profile]\((https://www\.hltv\.org/[^)]+)\)", block)
        if not team_match or not detail_match:
            continue

        after_team = block[team_match.end():].splitlines()
        roster: list[str] = []
        for line in after_team:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") or line.startswith("!["):
                break
            roster.append(_clean_markdown_label(line))
            if len(roster) == 5:
                break
        if len(roster) != 5:
            continue

        region_code = team_match.group(3)
        regional_counts[region_code] = regional_counts.get(region_code, 0) + 1
        rows.append(
            {
                "rank": int(marker.group(1)),
                "points": int(team_match.group(2)),
                "team": team_match.group(1).strip(),
                "roster": roster,
                "snapshot_date": snapshot_date,
                "region": REGION_NAMES[region_code],
                "regional_rank": regional_counts[region_code],
                "detail_path": "",
                "detail_url": detail_match.group(1).replace("&amp;", "&"),
                "team_url": team_url_match.group(1) if team_url_match else "",
                "source": "HLTV Live VRS (Beta)",
            }
        )
    if not rows:
        raise VRSDataError("HLTV's live VRS page did not contain any ranking rows.")
    return {
        "date": snapshot_date,
        "path": HLTV_LIVE_URL,
        "source": "HLTV Live VRS (Beta)",
    }, rows


def load_hltv_live_standings() -> tuple[dict[str, str], list[dict[str, Any]]]:
    return parse_hltv_standings(_get_text(f"{JINA_BASE}{HLTV_LIVE_URL}", timeout=30))


def _next_points(lines: list[str], label: str) -> float:
    for index, line in enumerate(lines):
        if line.strip().startswith(label):
            for candidate in lines[index + 1:index + 5]:
                match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*p\s*", candidate)
                if match:
                    return _float(match.group(1))
    return 0.0


def parse_hltv_team_detail(markdown: str, team_row: dict[str, Any]) -> dict[str, Any]:
    lines = markdown.splitlines()
    factors = {
        "LAN Wins": _next_points(lines, "LAN wins"),
        "Opponent Network": _next_points(lines, "Opponent network"),
        "Bounty Offered": _next_points(lines, "Bounty offered"),
        "Bounty Collected": _next_points(lines, "Bounty collected"),
        "Head To Head": _next_points(lines, "Head to head"),
    }
    if not any(factors.values()):
        raise VRSDataError("HLTV's VRS point breakdown could not be read.")

    section_names = {
        "Most recent LAN wins": "LAN Wins",
        "Opponent network, 10 best wins": "Opponent Network",
        "Bounty offered, 10 best prize winnings": "Bounty Offered",
        "Bounty collected, 10 best wins": "Bounty Collected",
        "Head to head matches": "Head To Head",
    }
    current_section = ""
    contributions: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if stripped in section_names:
            current_section = section_names[stripped]
            continue
        if not current_section or not stripped.startswith("|"):
            continue
        cells = _cells(stripped)
        if not cells or cells[0] == "Date" or set(cells[0]) <= {"-", ":"}:
            continue
        if not re.fullmatch(r"\d{2}/\d{2}/\d{2}", cells[0]):
            continue

        if current_section == "Bounty Offered":
            if len(cells) < 5:
                continue
            opponent, event, result = "", _clean_markdown_label(cells[1]), ""
        else:
            if len(cells) < 5:
                continue
            opponent = _clean_markdown_label(cells[1])
            event = _clean_markdown_label(cells[2])
            result = cells[-2].strip() if current_section == "Head To Head" else ""
        contributions.append(
            {
                "date": _iso_hltv_date(cells[0]),
                "opponent": opponent,
                "event": event,
                "component": current_section,
                "points": _float(cells[-1]),
                "result": result,
                "roster": list(team_row["roster"]),
            }
        )

    h2h_matches = [
        {
            "match_number": index + 1,
            "match_id": 0,
            "date": row["date"],
            "opponent": row["opponent"],
            "event": row["event"],
            "result": row["result"],
            "age_weight": 0.0,
            "event_weight": 0.0,
            "bounty_adjusted": 0.0,
            "network_adjusted": 0.0,
            "lan_adjusted": 0.0,
            "h2h": row["points"],
            "roster": list(team_row["roster"]),
        }
        for index, row in enumerate(contributions)
        if row["component"] == "Head To Head"
    ]
    return {
        "team": team_row["team"],
        "roster": list(team_row["roster"]),
        "global_rank": team_row["rank"],
        "region": team_row["region"],
        "regional_rank": team_row["regional_rank"],
        "final_score": float(team_row["points"]),
        "starting_score": 400.0 + sum(
            value for name, value in factors.items() if name != "Head To Head"
        ),
        "h2h_total": factors["Head To Head"],
        "factors": factors,
        "matches": h2h_matches,
        "contributions": contributions,
        "prizes": [],
        "source": "HLTV Live VRS (Beta)",
        "detail_url": team_row["detail_url"],
    }


def _enrich_historical_rosters(
    detail: dict[str, Any], official_detail: dict[str, Any] | None
) -> dict[str, Any]:
    if not official_detail or not official_detail.get("matches"):
        return detail
    official_matches = official_detail["matches"]
    exact = {
        (match["date"], _clean_markdown_label(match["opponent"]).casefold()): match["roster"]
        for match in official_matches
    }
    latest_official_date = max(match["date"] for match in official_matches)

    def roster_for(row: dict[str, Any]) -> list[str]:
        key = (row["date"], _clean_markdown_label(row.get("opponent", "")).casefold())
        if key in exact:
            return list(exact[key])
        if row["date"] > latest_official_date:
            return list(detail["roster"])
        prior = [match for match in official_matches if match["date"] <= row["date"]]
        return list(max(prior, key=lambda match: match["date"])["roster"]) if prior else list(detail["roster"])

    for row in detail["contributions"]:
        row["roster"] = roster_for(row)
    for row in detail["matches"]:
        row["roster"] = roster_for(row)
    return detail


def load_hltv_team_detail(
    team_row: dict[str, Any], official_detail: dict[str, Any] | None = None
) -> dict[str, Any]:
    detail_url = team_row.get("detail_url", "")
    if not detail_url.startswith("https://www.hltv.org/valve-ranking/teams/details/"):
        raise VRSDataError("Unexpected HLTV detail URL.")
    markdown = _get_text(f"{JINA_BASE}{detail_url}", timeout=30)
    return _enrich_historical_rosters(parse_hltv_team_detail(markdown, team_row), official_detail)


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

    contribution_rows: list[dict[str, Any]] = []
    event_groups: dict[str, dict[str, Any]] = {}
    if detail.get("contributions"):
        for contribution in detail["contributions"]:
            historical_keys = {normalize_player(name) for name in contribution["roster"]}
            overlap = len(simulated_keys & historical_keys)
            eligible = overlap >= 3
            status = "Retained" if overlap >= 4 else "At risk" if overlap == 3 else "Lost"
            row = {**contribution, "overlap": overlap, "eligible": eligible, "status": status}
            contribution_rows.append(row)
            event = contribution["event"] or "Other"
            group = event_groups.setdefault(
                event,
                {
                    "event": event,
                    "current_points": 0.0,
                    "retained_points": 0.0,
                    "lost_points": 0.0,
                    "rows": 0,
                    "eligible_rows": 0,
                },
            )
            group["current_points"] += contribution["points"]
            group["rows"] += 1
            if eligible:
                group["retained_points"] += contribution["points"]
                group["eligible_rows"] += 1
            else:
                group["lost_points"] += contribution["points"]

        retained_components: dict[str, float] = {}
        for component, headline_points in detail["factors"].items():
            component_rows = [
                row for row in contribution_rows if row["component"] == component
            ]
            if component == "Head To Head":
                retained_components[component] = (
                    headline_points
                    if component_rows and all(row["eligible"] for row in component_rows)
                    else sum(row["points"] for row in component_rows if row["eligible"])
                )
            else:
                listed_total = sum(row["points"] for row in component_rows)
                listed_retained = sum(
                    row["points"] for row in component_rows if row["eligible"]
                )
                retained_components[component] = (
                    headline_points * listed_retained / listed_total if listed_total else 0.0
                )
        positive_total = sum(
            value for name, value in detail["factors"].items() if name != "Head To Head"
        )
        positive_retained = sum(
            value for name, value in retained_components.items() if name != "Head To Head"
        )
        factor_ratio = positive_retained / positive_total if positive_total else 1.0
        all_eligible = bool(contribution_rows) and all(
            row["eligible"] for row in contribution_rows
        )
        indicative_score = (
            detail["final_score"]
            if all_eligible
            else max(400.0, 400.0 + sum(retained_components.values()))
        )
        for group in event_groups.values():
            group["status"] = (
                "Retained"
                if group["eligible_rows"] == group["rows"]
                else "Lost"
                if group["eligible_rows"] == 0
                else "Partial"
            )
    else:
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
        "contribution_rows": contribution_rows,
        "event_groups": sorted(
            event_groups.values(), key=lambda row: row["current_points"], reverse=True
        ),
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
