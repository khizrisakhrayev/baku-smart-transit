# AI Declaration

This project was built with AI assistance. Every AI-assisted task is logged below with its
timestamp, the tool used, the exact prompt, a short summary of what was generated, and the files changed.

---

## 2026-10-31 12:08
- **Tool:** Claude Code
- **Prompt:** "Read CLAUDE.md. Create the project skeleton, requirements.txt, and AI_DECLARATION.md with a header."
- **Summary:** Created the project skeleton (FastAPI app with health endpoint serving the static frontend, stub backend modules, placeholder Azerbaijani UI pages), dependencies, pytest config and a smoke test.
- **Files changed:** requirements.txt, pytest.ini, .gitignore, AI_DECLARATION.md, backend/app/{__init__,main,models,store,simulator,eta,anomaly}.py, frontend/{index,passenger,operator}.html, frontend/js/{passenger,operator}.js, frontend/css/style.css, tests/test_health.py

## 2026-10-31 12:16
- **Tool:** Claude Code
- **Prompt:** "Implement models.py, store.py and simulator.py. Use 3-4 real Baku bus routes (e.g. 1, 5, 65, 88) with real stop names and approximate coordinates. Each route has 2-3 buses that move along the stop sequence every 2s in a background task started on app startup. Add unit tests for the simulator."
- **Summary:** Added Stop/Route/Bus models, an in-memory store, 4 Baku routes (1, 5, 65, 88) and a round-trip GPS simulator (3 buses/route, 2s tick) started via FastAPI lifespan, plus /api/routes and /api/buses endpoints and simulator tests.
- **Files changed:** backend/app/models.py, backend/app/store.py, backend/app/routes_data.py, backend/app/simulator.py, backend/app/main.py, tests/test_simulator.py, tests/test_health.py, AI_DECLARATION.md

## 2026-10-31 12:19
- **Tool:** Claude Code
- **Prompt:** "Add the passenger API. GET /api/stops?route_id returns stops of a route. GET /api/stops/{stop_id}/eta returns, for each bus approaching that stop, minutes until arrival and current density, computed in eta.py from the bus position and simulator speed. POST /api/reports accepts {route_id, bus_id, level: low|medium|high} with validation, stores it with a timestamp in store.py, and returns the report. Each bus exposes its latest density level in /api/buses. Add unit tests for eta.py and API tests for these endpoints."
- **Summary:** Added stop ids, density report models and storage, ETA calculation (remaining segments × simulator segment time, soonest visit on the round trip) and the /api/stops, /api/stops/{stop_id}/eta and /api/reports endpoints, with unit and API tests.
- **Files changed:** backend/app/routes_data.py, backend/app/models.py, backend/app/store.py, backend/app/eta.py, backend/app/main.py, tests/test_simulator.py, tests/test_eta.py, tests/test_api.py, AI_DECLARATION.md

## 2026-10-31 12:26
- **Tool:** Claude Code
- **Prompt:** "Add the operator module.
1) Persist reports in SQLite (backend/data.db, stdlib sqlite3, created on startup; tests use a temp/in-memory DB).
2) GET /api/operator/density: per route, the dominant level from reports in the last ANOMALY_WINDOW_SEC, report counts per level, bus count, and last report time.
3) anomaly.py: a route is anomalous when it has had at least 3 reports, all \"high\", across a span of at least ANOMALY_WINDOW_SEC, with no low/medium report in between. Then create one active alert per route with the message \"Əlavə avtobus ehtiyatı ayrılmalıdır\", route_id and created_at. Do not duplicate active alerts. Check on each new report and every 10s in the background.
4) GET /api/operator/alerts (active first) and POST /api/operator/alerts/{id}/resolve.
5) Make ETA realistic: add SIM_TIME_SCALE in eta.py so one stop-to-stop segment shows as about 2-3 minutes.
6) Add POST /api/demo/flood-high?route_id to quickly send high reports for demo.
Unit-test the anomaly rule with fake timestamps (no sleeping) and API-test the endpoints."
- **Summary:** Moved reports and alerts to SQLite, added the anomaly rule with a background checker, per-route density overview, alert list/resolve endpoints, a demo flood endpoint (backdated high reports), and SIM_TIME_SCALE=15 for 2.5-minute segment ETAs; with anomaly unit tests and operator API tests.
- **Files changed:** backend/app/models.py, backend/app/store.py, backend/app/anomaly.py, backend/app/density.py, backend/app/eta.py, backend/app/main.py, tests/conftest.py, tests/test_anomaly.py, tests/test_operator_api.py, tests/test_api.py, tests/test_eta.py, AI_DECLARATION.md

## 2026-10-31 12:32
- **Tool:** Claude Code
- **Prompt:** "Small fix first: in demo flood-high, place the oldest report slightly inside the window so density shows high: 3.
Then build frontend/passenger.html + js/passenger.js + css/style.css (UI text in Azerbaijani, mobile-friendly, clean modern look).
- Route dropdown from /api/routes. Leaflet map with OpenStreetMap tiles centered on Baku, showing the route polyline and stops.
- Live bus markers from /api/buses?route_id, polled every 3s, marker color by density (green low, orange medium, red high, grey unknown).
- Clicking a stop (or a stop list) shows ETA list from /api/stops/{id}/eta: bus, minutes, density badge.
- Clicking a bus opens a panel with three buttons \"Aşağı / Orta / Yüksək\" that POST /api/reports and show a toast \"Təşəkkürlər, bildirişiniz qəbul edildi\".
Keep JS plain and readable, no build tools."
- **Summary:** Demo flood now adds one anchor report at the window start plus 3 inside the window (density shows high: 3, alert still fires); /api/buses accepts route_id. Built the passenger page: Leaflet map with route, stops, live density-colored bus markers, stop ETA list, bus report panel and toast.
- **Files changed:** backend/app/main.py, tests/test_api.py, tests/test_operator_api.py, frontend/passenger.html, frontend/js/passenger.js, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 12:36
- **Tool:** Claude Code
- **Prompt:** "Build frontend/operator.html + js/operator.js reusing css/style.css (Azerbaijani UI, desktop-first dashboard).
- Leaflet map with all routes drawn, each polyline colored by its dominant density from /api/operator/density (green/orange/red/grey), and live bus markers.
- Density table: route, buses, low/medium/high counts, dominant level badge, last report time.
- Alerts panel from /api/operator/alerts: active alerts highlighted in red with route and time, \"Həll edildi\" button calling resolve. Show a toast and a short sound/flash when a new alert appears.
- Summary cards on top: active buses, reports in window, active alerts.
- A small \"Demo\" button per route calling /api/demo/flood-high.
Poll every 3s. Add a nav link between passenger and operator pages. Also copy Leaflet into frontend/vendor so it works without CDN."
- **Summary:** Built the operator dashboard (summary cards, density-colored route map with live buses, density table with per-route Demo buttons, alerts panel with resolve, toast/beep/flash on new alerts, 3s polling), added passenger/operator nav, and vendored Leaflet 1.9.4 (hash-verified) into frontend/vendor/leaflet.
- **Files changed:** frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, frontend/passenger.html, frontend/vendor/leaflet/*, AI_DECLARATION.md
