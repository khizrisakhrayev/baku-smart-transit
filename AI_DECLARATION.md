# AI Declaration

This project was built with AI assistance. Every AI-assisted task is logged below with its
timestamp, the tool used, the exact prompt, a short summary of what was generated, and the files changed.

Timestamps are the time of the git commit that completed each task. (Earlier versions of this
file carried estimated times; they were corrected to the real commit times on 2026-10-31.)
An Azerbaijani version is in `AI_DECLARATION_AZ.md`.

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

## 2026-10-31 12:20
- **Tool:** Claude Code
- **Prompt:** "Add the passenger API. GET /api/stops?route_id returns stops of a route. GET /api/stops/{stop_id}/eta returns, for each bus approaching that stop, minutes until arrival and current density, computed in eta.py from the bus position and simulator speed. POST /api/reports accepts {route_id, bus_id, level: low|medium|high} with validation, stores it with a timestamp in store.py, and returns the report. Each bus exposes its latest density level in /api/buses. Add unit tests for eta.py and API tests for these endpoints."
- **Summary:** Added stop ids, density report models and storage, ETA calculation (remaining segments × simulator segment time, soonest visit on the round trip) and the /api/stops, /api/stops/{stop_id}/eta and /api/reports endpoints, with unit and API tests.
- **Files changed:** backend/app/routes_data.py, backend/app/models.py, backend/app/store.py, backend/app/eta.py, backend/app/main.py, tests/test_simulator.py, tests/test_eta.py, tests/test_api.py, AI_DECLARATION.md

## 2026-10-31 12:25
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

## 2026-10-31 12:30
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

## 2026-10-31 12:35
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

## 2026-10-31 12:49
- **Tool:** Claude Code
- **Prompt:** "Expand routes_data.py to 25 Baku bus routes using real route numbers and well-known real stop names with approximate coordinates. Reuse shared stop IDs where routes overlap (28-may, sahil, koroglu, genclik, nizami, elmler, icerisheher etc.). 2-3 buses per route. Add a comment that this is simplified demo data.
Keep the maps readable:
- passenger.html: add a search box to the route dropdown.
- operator.html: draw all routes as thin semi-transparent grey lines; draw routes with medium/high density or an active alert thick and colored. Show bus markers only for the selected route and alerted routes.
- operator sidebar: searchable route list, problem routes first; clicking a route highlights it and zooms to it.
- density table sorted by severity (alerts, high, medium, low, no data).
Update tests that assume 4 routes. Run pytest -q and commit.

Aim for 80-120 unique stops total, 8-12 stops per route, covering central Baku and districts (Yasamal, Nəsimi, Nərimanov, Xətai, Binəqədi, Sabunçu, Nizami, Suraxanı). Each stop: readable unique ID, Azerbaijani display name, lat/lon. Add a test that all stop IDs are unique and every route references existing stops."
- **Summary:** Rebuilt routes_data.py as a stop catalogue (89 stops across 8+ districts) and 25 routes (8-11 stops each, shared hub IDs) with a simplified-data disclaimer; added route search to the passenger page; operator map now greys idle routes, highlights problem/selected routes, shows buses only for selected/alerted routes, with a searchable severity-sorted route list and severity-sorted table. Added network data tests and updated 4-route assumptions.
- **Files changed:** backend/app/routes_data.py, tests/test_routes_data.py, tests/test_api.py, tests/test_health.py, frontend/passenger.html, frontend/js/passenger.js, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 12:55
- **Tool:** Claude Code
- **Prompt:** "Smart dispatch: when an anomaly alert is created, find a donor route with the most \"low\"/unknown density and at least 3 buses, and attach a recommendation to the alert: \"Marşrut X-dən 1 avtobusu Marşrut Y-ə yönləndirin\". Add POST /api/operator/alerts/{id}/dispatch that actually moves one bus in the simulator from donor to the target route and resolves the alert. Show the recommendation and a \"Təsdiqlə\" button in the operator alerts panel. Unit-test donor selection and the dispatch endpoint. Commit."
- **Summary:** Added dispatch.py (donor choice among calm, non-alerted routes with ≥3 buses; moving a bus to the alerted route), recommendation stored on new alerts (with a small SQLite column migration), POST /api/operator/alerts/{id}/dispatch, and a recommendation line with "Təsdiqlə" in the operator alerts panel; with donor-selection and dispatch tests.
- **Files changed:** backend/app/dispatch.py, backend/app/anomaly.py, backend/app/store.py, backend/app/models.py, backend/app/main.py, frontend/js/operator.js, frontend/css/style.css, tests/test_dispatch.py, AI_DECLARATION.md

## 2026-10-31 13:02
- **Tool:** Claude Code
- **Prompt:** "Two small fixes first:
- Move ANOMALY_WINDOW_SEC and other tunables into backend/app/config.py to break the anomaly -> dispatch -> density import loop.
- Avoid wrong Azerbaijani suffixes: change the recommendation text to \"Tövsiyə: Marşrut X → Marşrut Y (1 avtobus yönləndirin)\" and the dispatched text to \"Avtobus 30-3 → Marşrut H1\".
Then report trust (keep it simple, put logic in trust.py):
- Passenger page generates an anonymous client_id (localStorage) and sends it with reports.
- Rate limit: max 1 report per client per bus per 60s -> 429 with Azerbaijani message, shown as a toast.
- Optional lat/lon in the report: if given and more than 500 m from the bus, reject with 422 (\"Avtobusdan çox uzaqdasınız\"). Passenger page sends browser geolocation if allowed, otherwise skips.
- Time decay: in density, weight each report by freshness (linear from 1.0 now to 0 at window end) and expose a confidence score 0-1 per route based on number of unique clients and freshness. Show confidence as a small bar in the operator table.
- Demo flood uses distinct client_ids so it still works.
Unit-test the rate limit, distance check and weighting. Commit."
- **Summary:** Added config.py with all tunables (breaking the import loop) and suffix-free dispatch texts. Added trust.py (rate limit, haversine distance check, freshness weight, confidence), client_id/lat/lon on reports with a SQLite column migration, weighted dominant level + confidence in density, passenger client id/geolocation/error toasts, and an operator confidence bar; with trust unit and API tests.
- **Files changed:** backend/app/config.py, backend/app/trust.py, backend/app/density.py, backend/app/models.py, backend/app/store.py, backend/app/main.py, backend/app/anomaly.py, backend/app/dispatch.py, backend/app/simulator.py, backend/app/eta.py, frontend/js/passenger.js, frontend/js/operator.js, frontend/operator.html, frontend/css/style.css, tests/test_trust.py, tests/test_anomaly.py, tests/test_api.py, tests/test_dispatch.py, tests/test_eta.py, tests/test_health.py, tests/test_operator_api.py, tests/test_simulator.py, AI_DECLARATION.md

## 2026-10-31 13:07
- **Tool:** Claude Code
- **Prompt:** "Passenger alternatives (logic in alternatives.py):
- In GET /api/stops/{stop_id}/eta, for each bus with density \"high\", add a suggestion: the next bus arriving at the same stop (same or any other route serving the stop) with density low/medium/unknown, with its eta and an extra-wait in minutes. Only suggest it if extra wait <= 10 minutes.
- Passenger ETA card: under a crowded bus show \"💡 Bu avtobus doludur. {route} {eta} dəq sonra gəlir (sıxlıq: Orta)\" in a highlighted box.
- Also add a stop-level \"Ən rahat seçim\" badge on the least crowded bus within the next 15 minutes.
Unit-test the suggestion rules (same route, other route, too long wait, no alternative). Commit."
- **Summary:** Added alternatives.py (suggestion for each crowded bus: soonest non-high bus at or after it within 10 min; most comfortable known-calm bus within 15 min), suggestion/most_comfortable fields on the ETA endpoint, and the highlighted suggestion box and "⭐ Ən rahat seçim" badge on the passenger ETA card; with unit and API tests.
- **Files changed:** backend/app/alternatives.py, backend/app/models.py, backend/app/config.py, backend/app/main.py, frontend/js/passenger.js, frontend/css/style.css, tests/test_alternatives.py, AI_DECLARATION.md

## 2026-10-31 13:14
- **Tool:** Claude Code
- **Prompt:** "1) Simulator realism: give each bus a random start offset along its route (seeded, deterministic in tests) so arrivals spread out instead of bunching.
2) Synthetic background reports (config SYNTHETIC_REPORTS=1 by default, off in tests): every 5s generate a few reports with a rush-hour pattern, so central routes (through 28-may, koroglu, genclik) trend toward high and outer routes stay low. Use distinct synthetic client_ids.
3) Forecast (logic in forecast.py, readable): per route, compute a density score (low=1, medium=2, high=3) over recent time buckets, fit a simple linear trend, and predict the score 15 minutes ahead. Return predicted level and trend (rising/stable/falling) in GET /api/operator/forecast.
4) Early warning: if a route is predicted \"high\" in 15 min but not high now, show a yellow \"⚠ Proqnoz: 15 dəq sonra Yüksək sıxlıq gözlənilir\" item in the operator alerts panel (not a real alert), and a trend arrow ↑ → ↓ column in the density table.
Unit-test the trend fit and predicted levels with fixed data. Commit."
- **Summary:** Seeded per-route random start offsets in the simulator; synthetic.py background reports with a rush-hour wave on central routes; forecast.py (1-min buckets, least-squares trend, 15-min prediction, early warning) with GET /api/operator/forecast; operator early-warning items and trend arrows; forecast, synthetic and offset tests.
- **Files changed:** backend/app/config.py, backend/app/simulator.py, backend/app/synthetic.py, backend/app/forecast.py, backend/app/models.py, backend/app/main.py, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, tests/conftest.py, tests/test_forecast.py, tests/test_synthetic.py, AI_DECLARATION.md

## 2026-10-31 13:21
- **Tool:** Claude Code
- **Prompt:** "1) Performance: density/anomaly/forecast should query only reports within the needed time range (indexed SQL by route_id and timestamp), not full history.
2) Demo speed: add RUSH_PERIOD_MIN to config (default 30, demo 6) so early warnings appear within ~2 minutes in demo mode.
3) Analytics: GET /api/operator/analytics returns per-minute report counts by level for the last 30 minutes (whole network) and top 10 routes by weighted high share.
4) New operator section \"Analitika\" with Chart.js copied into frontend/vendor (no CDN): a stacked area chart of low/medium/high over time and a horizontal bar chart of the top 10 most crowded routes. Refresh every 10s, without re-creating charts (update data only).
5) Summary card \"Şəbəkə sıxlıq indeksi\" (0-100) on top.
Keep code readable. Test the analytics endpoint. Commit."
- **Summary:** Added SQLite indexes and time-ranged report queries (density, anomaly with a 2-window lookback, forecast); RUSH_PERIOD_MIN; analytics.py with GET /api/operator/analytics (30-min timeline, top-10 high share, network density index); operator "Analitika" section with vendored Chart.js 4.4.4 (stacked area + horizontal bar, updated in place, table view) and a density index card; analytics and query tests.
- **Files changed:** backend/app/store.py, backend/app/density.py, backend/app/anomaly.py, backend/app/forecast.py, backend/app/config.py, backend/app/synthetic.py, backend/app/analytics.py, backend/app/models.py, backend/app/main.py, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, frontend/vendor/chartjs/*, tests/test_analytics.py, tests/test_synthetic.py, AI_DECLARATION.md

## 2026-10-31 13:27
- **Tool:** Claude Code
- **Prompt:** "Add real-time push with Server-Sent Events: GET /api/stream emits \"buses\" every 2s and \"alert\" immediately when an alert is created or resolved. Use it in passenger.js and operator.js via EventSource; if the stream fails, fall back automatically to the existing polling. Show a small \"Canlı\" / \"Polling\" indicator in the header. Keep it simple, test the stream endpoint briefly. Commit."
- **Summary:** Added events.py (thread-safe in-process pub/sub + SSE stream with keep-alive) and GET /api/stream; the simulator publishes "buses" after each tick and the store publishes "alert" on create/resolve. Passenger and operator pages use EventSource with automatic fallback to polling and a Canlı/Polling header indicator; passenger now also removes markers of buses that left the route. Stream tests added.
- **Files changed:** backend/app/events.py, backend/app/main.py, backend/app/store.py, backend/app/simulator.py, backend/app/config.py, frontend/passenger.html, frontend/operator.html, frontend/js/passenger.js, frontend/js/operator.js, frontend/css/style.css, tests/test_stream.py, AI_DECLARATION.md

## 2026-10-31 13:45
- **Tool:** Claude Code
- **Prompt:** "UI polish only, no backend changes, keep code readable:
1) Bus markers: small inline SVG bus icon (front view) as a Leaflet divIcon, body colored by density (green/orange/red/grey), route number label, subtle shadow. Rotate or not, keep it simple.
2) Passenger page: allow selecting up to 3 routes at once as removable chips; each selected route gets its own distinct line color; bus icons keep density colors with a thin border in the route color. Show stop dots only at zoom >= 14 (except selected stop).
3) Operator page: reorganize into tabs \"Xəritə\", \"Alertlər\", \"Analitika\". Keep summary cards always visible on top. Alert count badge on the Alertlər tab.
4) Visual cleanup across both pages: consistent spacing scale, one font (system-ui), max 3 accent colors plus density colors, rounded cards with light shadow, clear headings, empty states with short helpful text, nothing overlapping on 1366x768 and mobile width.
Update common.js/style.css rather than duplicating. Run pytest -q and commit."
- **Summary:** Added js/common.js (shared API/formatting/toast/map/live-stream helpers, SVG bus icon and marker sync) used by both pages; passenger page now supports up to 3 route chips with validated distinct line colors, route-colored bus outlines and zoom-dependent stop dots; operator page reorganized into Xəritə/Alertlər/Analitika tabs with an alert count badge; style.css rewritten around a spacing/type scale, one font and 3 accent colors, with empty states; landing page restyled. No backend changes.
- **Files changed:** frontend/js/common.js, frontend/js/passenger.js, frontend/js/operator.js, frontend/passenger.html, frontend/operator.html, frontend/index.html, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 13:53
- **Tool:** Claude Code
- **Prompt:** "Change the default of MAX_REPORT_DISTANCE_M in config.py to 0 (disabled), since GPS is simulated. Keep the feature: document in README/config that setting it to e.g. 500 enables the proximity check for real GPS. Update tests accordingly, run pytest -q and commit."
- **Summary:** Proximity check now off by default (MAX_REPORT_DISTANCE_M=0) with docs in config.py, trust.py and a new README.md (run, demo mode, settings); distance tests enable the check explicitly and new tests cover the disabled default.
- **Files changed:** backend/app/config.py, backend/app/trust.py, README.md, tests/test_trust.py, AI_DECLARATION.md

## 2026-10-31 14:03
- **Tool:** Claude Code
- **Prompt:** "Two small UX fixes, no rule changes:
1) Passenger page: persist selected routes and selected stop in localStorage and restore them on load, so switching to Operator and back keeps the selection.
2) Operator page: for routes whose latest reports are \"high\" but no alert yet, show a pending indicator in the Alertlər tab and the route list: \"Yüksək sıxlıq izlənilir: 1/3 bildiriş, alertə qədər ~X san\". Expose this from the anomaly logic (count in current high run and seconds remaining to reach the window). Add a short help text: \"Alert üçün xətt ANOMALY_WINDOW_SEC ərzində ardıcıl Yüksək qalmalıdır\".
Test the pending calculation. Run pytest -q and commit."
- **Summary:** Passenger selection (routes + stop) saved to and restored from localStorage. anomaly.py gains pending_status/pending (sharing the rule's report window and "already handled" check, rule unchanged) exposed via GET /api/operator/pending; operator shows pending items, ⏳ tags in the route list and the rule help text with the real window. Pending unit and API tests added.
- **Files changed:** backend/app/anomaly.py, backend/app/models.py, backend/app/main.py, frontend/js/passenger.js, frontend/js/operator.js, frontend/operator.html, frontend/css/style.css, tests/test_anomaly.py, tests/test_operator_api.py, AI_DECLARATION.md

## 2026-10-31 14:05
- **Tool:** Claude Code
- **Prompt:** "Simulator tuning, config only where possible:
1) Slow buses down so movement on the map looks realistic: one stop-to-stop segment should take about 30s of real time instead of 10s, still moving smoothly every 2s. Adjust SIM_TIME_SCALE so displayed ETAs stay realistic (~2-3 min per segment) and remain consistent with the new speed.
2) Variable fleet size: central/busy routes (through 28-may, koroglu, genclik, nizami) get 4-5 buses, outer routes keep 3. Make it a per-route value in routes_data.py with the default from config.
Update tests that assume a fixed bus count or speed. Run pytest -q and commit."
- **Summary:** STEPS_PER_SEGMENT 5 -> 15 (30s per segment at 2s ticks) and SIM_TIME_SCALE 15 -> 5 (still 2.5 min shown per segment). Route.bus_count with FLEET_SIZE in routes_data.py (5 buses for routes through 2+ hubs, 4 through one, default 3 from config); simulator uses it. Tests now derive counts from each route; new fleet-size and speed tests.
- **Files changed:** backend/app/config.py, backend/app/eta.py, backend/app/models.py, backend/app/routes_data.py, backend/app/simulator.py, tests/test_api.py, tests/test_dispatch.py, tests/test_eta.py, tests/test_health.py, tests/test_operator_api.py, tests/test_routes_data.py, tests/test_simulator.py, tests/test_stream.py, AI_DECLARATION.md

## 2026-10-31 14:20
- **Tool:** Claude Code
- **Prompt:** "Two operator page fixes, keep it small:
1) Slow load (~30s before routes appear): find the cause first (likely many sequential per-route requests, N+1 SQL queries, or SSE/polling blocking initial fetches). Fix it: add one GET /api/operator/overview that returns routes with geometry, density, pending, alerts and forecast in a single response with batched SQL; render the map from it immediately, then start SSE and polling. Target: page usable in under 2s. Report what the cause was.
2) Network overview: on load, fit the map to the central Baku bounds of all routes (not the whole region). Make non-problem routes visible but calm (thin grey, ~0.5 opacity instead of nearly invisible), problem routes thick and colored, and show a small \"Şəbəkə görünüşü\" button that resets the view.
Run pytest -q and commit."
- **Summary:** Root cause: the shared SQLite connection was used concurrently by request threads and background tasks without a lock, so parallel page requests failed (13/20 polls) and the page stayed empty until a poll fully succeeded; secondary: `localhost` costs ~2s per new connection on Windows (IPv6 first). Fixed with a locked store (_query/_write), a batched GET /api/operator/overview (3 SQL statements instead of 199 per poll, same numbers via shared pure functions), and an operator page that paints from one overview call before starting SSE/polling. Network view fits the central 5–95 percentile bounds, idle routes at 0.5 opacity, "Şəbəkə görünüşü" button. Overview and concurrency tests; README note on 127.0.0.1.
- **Files changed:** backend/app/store.py, backend/app/overview.py, backend/app/density.py, backend/app/forecast.py, backend/app/anomaly.py, backend/app/models.py, backend/app/main.py, frontend/js/operator.js, frontend/css/style.css, tests/test_overview.py, README.md, AI_DECLARATION.md

## 2026-10-31 14:30
- **Tool:** Claude Code
- **Prompt:** "Final submission package, no new features:
1) dispatch.py tie-break: prefer donor routes not passing a hub, then more buses.
2) tests/test_integration.py: full flow report -> density -> alert -> dispatch -> resolved.
3) Dockerfile (python:3.12-slim, uvicorn 0.0.0.0:8000), docker-compose.yml with env vars + volume for data.db, .env.demo, run_demo.ps1 (Windows, starts from backend/).
4) Expand README.md (keep existing): Azerbaijani summary on top, features, screenshots placeholders docs/screenshots/*.png, run locally (http://127.0.0.1:8000) / Docker / tests, demo script for judges, Mermaid architecture diagram, API table, limitations, team roles (Ülvi Mustafayev - Backend & API; Anar Hümmətli - Frontend & UI/UX; Xizri Saxrayev - AI integration, testing & documentation).
5) docs/TEXNIKI_IZAH.md in formal Azerbaijani: problem context, solution, architecture and data flow, technologies and why, project structure, key algorithms (ETA, anomaly rule, smart dispatch, report trust/confidence, forecast, alternatives), testing approach and results, the SQLite concurrency bug found and fixed, limitations, future development (real BakuBus GPS/GTFS, BakuCard data, mobile app, ML forecasting, PostgreSQL, auth).
6) AI_DECLARATION_AZ.md: Azerbaijani version of AI_DECLARATION.md with a summary of tools used (Claude Code in VS Code for code/tests/docs, Claude for planning and prompt design), how and for which parts, keeping every prompt in original English.
Run pytest -q and commit."
- **Summary:** Dispatch tie-break now prefers donor routes that pass no hub (HUB_STOP_IDS in config), then more buses; end-to-end integration test; Dockerfile, docker-compose.yml, .env.demo, run_demo.ps1; expanded README (Azerbaijani summary, features, screenshot placeholders, run/Docker/tests, judge demo script, Mermaid architecture, API table, limitations, team); docs/TEXNIKI_IZAH.md; AI_DECLARATION_AZ.md. Corrected the timestamps of all earlier entries in this file to the real commit times (they had been estimated).
- **Files changed:** backend/app/dispatch.py, backend/app/config.py, tests/test_dispatch.py, tests/test_integration.py, Dockerfile, .dockerignore, docker-compose.yml, .env.demo, run_demo.ps1, README.md, docs/screenshots/README.md, docs/TEXNIKI_IZAH.md, AI_DECLARATION.md, AI_DECLARATION_AZ.md
