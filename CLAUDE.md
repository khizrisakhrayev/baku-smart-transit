# Baku Smart Transit & Crowdsourcing Engine (4h hackathon prototype)
Stack: Python 3.11, FastAPI, in-memory store + SQLite, vanilla HTML/JS, Leaflet + OpenStreetMap tiles, pytest.
Layout: backend/app (main.py, models.py, store.py, simulator.py, eta.py, anomaly.py), frontend/ (passenger.html, operator.html, js/, css/), tests/.
Rules:
- Keep it simple. No extra frameworks. FastAPI serves frontend via StaticFiles.
- GPS simulator: 3-4 real Baku bus routes with real stop names and coordinates; buses move every 2s.
- Density levels: low / medium / high. Anomaly: if a route is reported "high" continuously for 10 minutes, create operator alert "Əlavə avtobus ehtiyatı ayrılmalıdır". Window configurable via env ANOMALY_WINDOW_SEC (default 600, demo 30).
- UI text in Azerbaijani; code and comments in English.
- After every task run `pytest -q` and commit with a clear message.
- AI DECLARATION: after every task, append to AI_DECLARATION.md: timestamp, tool (Claude Code), the user's prompt verbatim, a 1-2 line summary of what was generated, and files changed. Never skip this.
Code style:
- Readable over clever. Small functions, clear names, short docstrings. A judge should understand any file in 1 minute.
- No over-engineering: no abstract base classes, factories, DI containers or extra layers unless they solve a real problem here.
- Complex logic (e.g. ETA calculation, sliding-window anomaly detection) is fine when needed, but isolate it in its own module and explain it with a brief comment.
- Prefer the standard library and FastAPI built-ins over new dependencies.
- Don't refactor working code unless asked.