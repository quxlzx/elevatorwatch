"""Data sources for WMATA elevator/escalator status.

Two sources:
  * scrape  — parses WMATA's public elevator status page (no API key needed).
  * api     — official WMATA developer API (free key from https://developer.wmata.com,
              set env WMATA_API_KEY).

`auto` tries api first when a key is present, otherwise scrape.
"""

import html
import json
import os
import re
import urllib.request

STATUS_PAGE_URL = "https://www.wmata.com/ride/elevators-escalators/status.html"
API_BASE = "https://api.wmata.com"
USER_AGENT = "elevatorwatch/0.1 (open-source transit accessibility tool)"

LINE_COLORS = {
    "#00B140": "G", "#DC241F": "R", "#009DDE": "O", "#FFC726": "Y", "#9370DB": "B",
}


def _get(url: str, headers: dict = None, timeout: int = 30) -> bytes:
    default_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) elevatorwatch/0.1 (open-source transit accessibility tool)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    }
    default_headers.update(headers or {})
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------- scrape ---

_STATION_MARK = 'cmp-elevator-escalator-status__station-name">'
_UNIT_RE = re.compile(
    r'<li class="cmp-elevator-escalator-status__unit-item(?P<cls>[^"]*)">(?P<body>.*?)</li>',
    re.S,
)
_HIDDEN_RE = re.compile(r'visually-hidden">\s*(In service|Out of service):')
_DESC_RE = re.compile(r'entrance-label">\s*<p>\s*(?P<d>[^<]+?)\s*</p>')
_REASON_RE = re.compile(r'unit-reason-label">\s*(?P<r>[^<]+?)\s*<')
_RETURN_RE = re.compile(r'unit-return">\s*(?P<t>[^<]+?)\s*<')
_LINE_ICON_RE = re.compile(r'line-icon[^>]*>\s*(?P<letter>[ROYGB])\s*<', re.I)


def fetch_scrape() -> list:
    """Parse the public status page into Unit objects (linear scan, no backtracking)."""
    from .model import Unit

    page = _get(STATUS_PAGE_URL).decode("utf-8", "replace")

    # Station headers appear in document order; slice each station's region
    # as the span between one header and the next.
    marks = [m for m in _iter_marks(page, _STATION_MARK)]
    units = []
    for i, start in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else len(page)
        region = page[start:end]

        name_part = region[len(_STATION_MARK):].split("<", 1)[0]
        station = html.unescape(name_part).strip()
        if not station:
            continue
        lines = sorted({lg.upper() for lg in _LINE_ICON_RE.findall(region[:1200])})

        for um in _UNIT_RE.finditer(region):
            body, cls = um.group("body"), um.group("cls")
            hid = _HIDDEN_RE.search(body)
            if hid:
                in_service = hid.group(1) == "In service"
            else:
                in_service = "--outage" not in cls
            desc_m = _DESC_RE.search(body)
            if not desc_m:
                continue
            desc = html.unescape(desc_m.group("d").strip())
            kind = "escalator" if desc.lower().startswith("escalator") else "elevator"
            reason_m = _REASON_RE.search(body)
            ret_m = _RETURN_RE.search(body)
            units.append(Unit(
                station=station,
                kind=kind,
                location=desc,
                lines=lines,
                in_service=in_service,
                reason=html.unescape(reason_m.group("r")) if reason_m else "",
                return_estimate=html.unescape(ret_m.group("t")) if ret_m else "",
            ))
    return units


def _iter_marks(page: str, mark: str):
    pos = 0
    while True:
        pos = page.find(mark, pos)
        if pos < 0:
            return
        yield pos
        pos += len(mark)


# ------------------------------------------------------------------- api ---

def fetch_api(key: str = None) -> list:
    """Official API: /Incidents.svc/json/ElevatorIncidents (needs free key)."""
    from .model import Unit

    key = key or os.environ.get("WMATA_API_KEY", "")
    data = json.loads(_get(f"{API_BASE}/Incidents.svc/json/ElevatorIncidents",
                           headers={"Ocp-Apim-Subscription-Key": key}))
    units = []
    for e in data.get("ElevatorIncidents", []):
        units.append(Unit(
            station=e.get("StationName", ""),
            kind="elevator",
            location=e.get("ElevatorLocation", ""),
            in_service=str(e.get("Status", "")).upper() != "OUT OF SERVICE",
            reason=e.get("Reason", "") or "",
            return_estimate=e.get("EstimatedInServiceDate", "") or "",
            station_code=e.get("StationCode", ""),
        ))
    return units


def fetch(source: str = "auto") -> list:
    if source == "scrape":
        return fetch_scrape()
    if source == "api":
        return fetch_api()
    if os.environ.get("WMATA_API_KEY"):
        try:
            return fetch_api()
        except Exception:
            pass
    return fetch_scrape()
