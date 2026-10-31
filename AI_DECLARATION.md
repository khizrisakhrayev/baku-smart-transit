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
