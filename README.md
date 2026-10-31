# Baku Smart Transit & Crowdsourcing Engine

Hackathon prototype: live (simulated) Baku buses, passenger crowd-density reports,
anomaly alerts with smart dispatch, forecasts and analytics for operators.

- Passenger page: `/passenger.html` — map, stop arrival times, report how full a bus is.
- Operator page: `/operator.html` — density map, alerts, forecast, analytics.

Stack: Python 3.11+, FastAPI, SQLite, vanilla HTML/JS, Leaflet, Chart.js (both vendored).

## Run

```bash
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/. (On Windows, `localhost` is tried as IPv6 first; uvicorn
listens on IPv4 only, so every new connection via `localhost` can lose up to ~2s.)

**Demo mode** (alerts and forecast warnings within a couple of minutes), PowerShell:

```powershell
$env:ANOMALY_WINDOW_SEC = "30"; $env:RUSH_PERIOD_MIN = "6"
uvicorn app.main:app
```

## Tests

```bash
pytest -q
```

## Settings

All tunables live in `backend/app/config.py`. These can be set as environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `DB_PATH` | `backend/data.db` | SQLite file for reports and alerts |
| `ANOMALY_WINDOW_SEC` | `600` | How long a route must stay "high" before an alert (demo: `30`) |
| `RUSH_PERIOD_MIN` | `30` | Length of the synthetic rush-hour wave (demo: `6`) |
| `SYNTHETIC_REPORTS` | `1` | Generate background demo reports (`0` = off) |
| `SIM_SEED` | `42` | Seed for the buses' start positions |
| `MAX_REPORT_DISTANCE_M` | `0` | Proximity check, see below |

### Proximity check (`MAX_REPORT_DISTANCE_M`)

When the passenger's browser shares its location, a report can be rejected if the
passenger is too far from the bus ("Avtobusdan çox uzaqdasınız"). It is **off by
default** (`0`) because bus positions are simulated, so a real phone is never near them.
With real bus GPS, enable it with a distance in metres, e.g. `MAX_REPORT_DISTANCE_M=500`.

## Data note

Route numbers and stop names are real; coordinates are approximate and stop sequences
are simplified demo data, not official BakuBus routes.

## AI declaration

Every AI-assisted change is logged in `AI_DECLARATION.md`.
