from __future__ import annotations

import html
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RDY_ROSTER_URL = "https://rdy.gg/en/cs2/stats?tab=roster-simulator"
USER_AGENT = "VRS-Roster-Lab/0.3"
MAX_PAGE_BYTES = 10_000_000


def _clean_page(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\\u0026", "&").replace("\\\"", '"')
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value)


def extract_rdy_overall_role(page: str, nickname: str) -> dict | None:
    """Extract RDY's rendered 'player (team, role, score)' roster entry."""
    cleaned = _clean_page(page)
    escaped_name = re.escape(nickname)
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){escaped_name}\s*\(\s*"
        rf"([^,()]+?)\s*,\s*([^,()]+?)\s*,\s*"
        rf"(\d+(?:\.\d+)?)\s*\)",
        re.IGNORECASE,
    )
    match = pattern.search(cleaned)
    if not match:
        return None
    return {
        "team": match.group(1).strip(),
        "overall_role": match.group(2).strip(),
        "role_score": float(match.group(3)),
    }


def _fetch_rdy_page() -> str:
    request = Request(
        RDY_ROSTER_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(MAX_PAGE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"RDY role data could not be loaded: {exc}") from exc
    if len(payload) > MAX_PAGE_BYTES:
        raise RuntimeError("RDY role page exceeded the safe response-size limit.")
    return payload.decode("utf-8", errors="replace")


def load_rdy_role_profile(nickname: str) -> dict:
    """Return a normalized, non-throwing role-source record for the app."""
    try:
        match = extract_rdy_overall_role(_fetch_rdy_page(), nickname)
    except RuntimeError:
        match = None
    if match:
        return {
            "player": nickname,
            **match,
            "source": "RDY roster simulator",
            "source_url": RDY_ROSTER_URL,
            "status": "Overall role only",
            "position_coverage": 0,
        }
    return {
        "player": nickname,
        "team": None,
        "overall_role": None,
        "role_score": None,
        "source": "RDY roster simulator",
        "source_url": RDY_ROSTER_URL,
        "status": "No structured role found",
        "position_coverage": 0,
    }
