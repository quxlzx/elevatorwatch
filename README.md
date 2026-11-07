# elevatorwatch

**Track WMATA elevator/escalator outages for the stations you actually care about — and get told the moment they break or come back.**

Washington Metro publishes elevator status, but only if you go look for it. If you use the elevator at your home station every day (stroller, wheelchair, bike, or just not wanting the stairs in July), you find out it's broken *at the platform*. `elevatorwatch` flips that: it polls the status feed, diffs against what it saw last time, and prints only the transitions.

Unofficial tool; not affiliated with WMATA.

## Quickstart

No dependencies — Python 3.9+ stdlib only.

```bash
python3 -m elevatorwatch status                      # every current outage
python3 -m elevatorwatch status --station "College Park"
python3 -m elevatorwatch status --station G          # filter by line letter
python3 -m elevatorwatch status --json               # machine-readable

# cron-friendly: poll once, print only what changed since last run
python3 -m elevatorwatch watch --stations "College Park-U of Md" "Fort Totten"
```

`watch` keeps state in `~/.elevatorwatch/state.json`. First run seeds silently;
after that it prints lines like:

```
🔴 OUT: Arlington Cemetery — Escalator between street and mezzanine south side of Memorial Drive (Minor Repair) — Estimated return to service: November 8, 2026 at 11:59 PM
🟢 BACK: Fort Totten — Escalator between platform and mezzanine
```

Exit code is `1` when there are new outages, `0` otherwise — easy to wire into
any scheduler:

```cron
*/5 * * * * out=$(elevatorwatch watch --stations "College Park-U of Md") && [ -n "$out" ] && notify "$out"
```

## Data sources

| source | what | needs key? |
|---|---|---|
| `scrape` (default) | WMATA's public elevator/escalator status page | no |
| `api` | `https://api.wmata.com/Incidents.svc/json/ElevatorIncidents` | free key from [developer.wmata.com](https://developer.wmata.com), set `WMATA_API_KEY` |

`--source auto` (default) uses the official API when `WMATA_API_KEY` is set and falls back to scraping. The scraper is a linear, non-backtracking HTML parse of the station blocks — it reports station name, line colors, unit location text, outage reason, and estimated return-to-service date.

## Roadmap

- [ ] Outage history: append every transition to SQLite, then stats per station ("this elevator has been out 47 of the last 90 days")
- [ ] Step-free trip check: given two stations, verify elevators work at both ends and at transfer stations before you leave
- [ ] GTFS-RT alerts source (`gtfs-metro-alert` API) and escalator parity in the API source
- [ ] Notification adapters (ntfy, Discord webhook, email)
- [ ] Planned-maintenance ("future updates") table parsing

## Disclaimer

Data belongs to WMATA. If they'd rather API-only, the `api` source is the supported path — the scraper exists because the official feed needs a signup wall for a free key.

## License

MIT
