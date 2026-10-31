# Süni intellektdən istifadə bəyannaməsi

Bu sənəd `AI_DECLARATION.md` faylının Azərbaycan dilində versiyasıdır. Layihə süni intellekt
alətlərinin köməyi ilə hazırlanıb. Süni intellektlə yerinə yetirilən hər tapşırıq aşağıda
qeyd olunub: vaxt, istifadə olunan alət, verilmiş tapşırığın (prompt) orijinal mətni,
yaradılanların qısa xülasəsi və dəyişdirilmiş fayllar.

## İstifadə olunan alətlər

| Alət | Necə istifadə olunub | Layihənin hansı hissələri üçün |
|---|---|---|
| **Claude Code** (VS Code genişlənməsi) | Komanda tapşırıqları ingilis dilində yazılmış promptlarla verib. Claude Code layihənin qaydalarını (`CLAUDE.md`) oxuyub kodu yazıb, `pytest -q` ilə testləri işə salıb, nəticəni yoxlayıb, bu bəyannaməyə qeyd əlavə edib və dəyişiklikləri commit edib. | Backend (FastAPI, alqoritmlər, SQLite), frontend (HTML/CSS/JS), testlər, sənədlər (README, texniki izah, bu bəyannamə), Docker faylları. |
| **Claude** (söhbət interfeysi) | Layihənin planlaşdırılması və Claude Code üçün promptların hazırlanması. | Funksiyaların sıralanması, tapşırıqların tərtibi və mərhələlərə bölünməsi. |

**Qeydlər:**
- Promptlar dəyişdirilmədən, **orijinal ingilis dilində** saxlanılıb; xülasələr Azərbaycan
  dilinə tərcümə olunub. Fayl adları və kod identifikatorları olduğu kimi saxlanılıb.
- Vaxt hər tapşırığı tamamlayan git commit-in vaxtıdır (Bakı vaxtı, UTC+4).
- Hər tapşırıqdan sonra bütün testlər (`pytest -q`) işə salınıb.

---

## 2026-10-31 12:08
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Read CLAUDE.md. Create the project skeleton, requirements.txt, and AI_DECLARATION.md with a header."
- **Xülasə:** Layihə skeleti yaradıldı: statik frontend-i təqdim edən və sağlamlıq endpointi olan FastAPI tətbiqi, backend modullarının ilkin faylları, Azərbaycan dilində ilkin UI səhifələri, asılılıqlar, pytest konfiqurasiyası və ilkin test.
- **Dəyişdirilmiş fayllar:** requirements.txt, pytest.ini, .gitignore, AI_DECLARATION.md, backend/app/{__init__,main,models,store,simulator,eta,anomaly}.py, frontend/{index,passenger,operator}.html, frontend/js/{passenger,operator}.js, frontend/css/style.css, tests/test_health.py

## 2026-10-31 12:16
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Implement models.py, store.py and simulator.py. Use 3-4 real Baku bus routes (e.g. 1, 5, 65, 88) with real stop names and approximate coordinates. Each route has 2-3 buses that move along the stop sequence every 2s in a background task started on app startup. Add unit tests for the simulator."
- **Xülasə:** Stop/Route/Bus modelləri, yaddaşda saxlanan store, 4 Bakı marşrutu (1, 5, 65, 88) və FastAPI lifespan ilə başladılan gediş-dönüş GPS simulyatoru (marşrut başına 3 avtobus, 2 saniyəlik addım), /api/routes və /api/buses endpointləri və simulyator testləri əlavə edildi.
- **Dəyişdirilmiş fayllar:** backend/app/models.py, backend/app/store.py, backend/app/routes_data.py, backend/app/simulator.py, backend/app/main.py, tests/test_simulator.py, tests/test_health.py, AI_DECLARATION.md

## 2026-10-31 12:20
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Add the passenger API. GET /api/stops?route_id returns stops of a route. GET /api/stops/{stop_id}/eta returns, for each bus approaching that stop, minutes until arrival and current density, computed in eta.py from the bus position and simulator speed. POST /api/reports accepts {route_id, bus_id, level: low|medium|high} with validation, stores it with a timestamp in store.py, and returns the report. Each bus exposes its latest density level in /api/buses. Add unit tests for eta.py and API tests for these endpoints."
- **Xülasə:** Dayanacaq identifikatorları, sıxlıq bildirişi modelləri və onların saxlanması, gəliş vaxtının hesablanması (qalan seqmentlər × simulyatorun seqment vaxtı, gediş-dönüş yolunda ən yaxın gəliş) və /api/stops, /api/stops/{stop_id}/eta, /api/reports endpointləri, modul və API testləri əlavə edildi.
- **Dəyişdirilmiş fayllar:** backend/app/routes_data.py, backend/app/models.py, backend/app/store.py, backend/app/eta.py, backend/app/main.py, tests/test_simulator.py, tests/test_eta.py, tests/test_api.py, AI_DECLARATION.md

## 2026-10-31 12:25
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Add the operator module.
1) Persist reports in SQLite (backend/data.db, stdlib sqlite3, created on startup; tests use a temp/in-memory DB).
2) GET /api/operator/density: per route, the dominant level from reports in the last ANOMALY_WINDOW_SEC, report counts per level, bus count, and last report time.
3) anomaly.py: a route is anomalous when it has had at least 3 reports, all \"high\", across a span of at least ANOMALY_WINDOW_SEC, with no low/medium report in between. Then create one active alert per route with the message \"Əlavə avtobus ehtiyatı ayrılmalıdır\", route_id and created_at. Do not duplicate active alerts. Check on each new report and every 10s in the background.
4) GET /api/operator/alerts (active first) and POST /api/operator/alerts/{id}/resolve.
5) Make ETA realistic: add SIM_TIME_SCALE in eta.py so one stop-to-stop segment shows as about 2-3 minutes.
6) Add POST /api/demo/flood-high?route_id to quickly send high reports for demo.
Unit-test the anomaly rule with fake timestamps (no sleeping) and API-test the endpoints."
- **Xülasə:** Bildirişlər və xəbərdarlıqlar SQLite-a köçürüldü; fon yoxlaması ilə anomaliya qaydası, marşrutlar üzrə sıxlıq icmalı, xəbərdarlıqların siyahısı və həlli üçün endpointlər, demo flood endpointi (keçmiş tarixli "Yüksək" bildirişlər) və 2,5 dəqiqəlik seqment ETA-sı üçün SIM_TIME_SCALE=15 əlavə edildi; anomaliya modul testləri və operator API testləri yazıldı.
- **Dəyişdirilmiş fayllar:** backend/app/models.py, backend/app/store.py, backend/app/anomaly.py, backend/app/density.py, backend/app/eta.py, backend/app/main.py, tests/conftest.py, tests/test_anomaly.py, tests/test_operator_api.py, tests/test_api.py, tests/test_eta.py, AI_DECLARATION.md

## 2026-10-31 12:30
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Small fix first: in demo flood-high, place the oldest report slightly inside the window so density shows high: 3.
Then build frontend/passenger.html + js/passenger.js + css/style.css (UI text in Azerbaijani, mobile-friendly, clean modern look).
- Route dropdown from /api/routes. Leaflet map with OpenStreetMap tiles centered on Baku, showing the route polyline and stops.
- Live bus markers from /api/buses?route_id, polled every 3s, marker color by density (green low, orange medium, red high, grey unknown).
- Clicking a stop (or a stop list) shows ETA list from /api/stops/{id}/eta: bus, minutes, density badge.
- Clicking a bus opens a panel with three buttons \"Aşağı / Orta / Yüksək\" that POST /api/reports and show a toast \"Təşəkkürlər, bildirişiniz qəbul edildi\".
Keep JS plain and readable, no build tools."
- **Xülasə:** Demo flood indi pəncərənin əvvəlinə bir dayaq bildirişi və pəncərənin içinə 3 bildiriş əlavə edir (sıxlıqda high: 3 görünür, xəbərdarlıq yenə yaranır); /api/buses route_id qəbul edir. Sərnişin səhifəsi quruldu: marşrut və dayanacaqlarla Leaflet xəritəsi, sıxlığa görə rənglənən canlı avtobus markerləri, dayanacaq üzrə ETA siyahısı, bildiriş paneli və təşəkkür mesajı (toast).
- **Dəyişdirilmiş fayllar:** backend/app/main.py, tests/test_api.py, tests/test_operator_api.py, frontend/passenger.html, frontend/js/passenger.js, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 12:35
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Build frontend/operator.html + js/operator.js reusing css/style.css (Azerbaijani UI, desktop-first dashboard).
- Leaflet map with all routes drawn, each polyline colored by its dominant density from /api/operator/density (green/orange/red/grey), and live bus markers.
- Density table: route, buses, low/medium/high counts, dominant level badge, last report time.
- Alerts panel from /api/operator/alerts: active alerts highlighted in red with route and time, \"Həll edildi\" button calling resolve. Show a toast and a short sound/flash when a new alert appears.
- Summary cards on top: active buses, reports in window, active alerts.
- A small \"Demo\" button per route calling /api/demo/flood-high.
Poll every 3s. Add a nav link between passenger and operator pages. Also copy Leaflet into frontend/vendor so it works without CDN."
- **Xülasə:** Operator paneli quruldu (ümumi göstərici kartları, sıxlığa görə rənglənən marşrut xəritəsi və canlı avtobuslar, hər marşrut üçün Demo düyməsi olan sıxlıq cədvəli, həll düyməsi olan xəbərdarlıq paneli, yeni xəbərdarlıqda toast, səs və işıqlanma, 3 saniyəlik yeniləmə); sərnişin/operator naviqasiyası əlavə edildi, Leaflet 1.9.4 (hash ilə yoxlanılmış) frontend/vendor/leaflet qovluğuna köçürüldü.
- **Dəyişdirilmiş fayllar:** frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, frontend/passenger.html, frontend/vendor/leaflet/*, AI_DECLARATION.md

## 2026-10-31 12:49
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Expand routes_data.py to 25 Baku bus routes using real route numbers and well-known real stop names with approximate coordinates. Reuse shared stop IDs where routes overlap (28-may, sahil, koroglu, genclik, nizami, elmler, icerisheher etc.). 2-3 buses per route. Add a comment that this is simplified demo data.
Keep the maps readable:
- passenger.html: add a search box to the route dropdown.
- operator.html: draw all routes as thin semi-transparent grey lines; draw routes with medium/high density or an active alert thick and colored. Show bus markers only for the selected route and alerted routes.
- operator sidebar: searchable route list, problem routes first; clicking a route highlights it and zooms to it.
- density table sorted by severity (alerts, high, medium, low, no data).
Update tests that assume 4 routes. Run pytest -q and commit.

Aim for 80-120 unique stops total, 8-12 stops per route, covering central Baku and districts (Yasamal, Nəsimi, Nərimanov, Xətai, Binəqədi, Sabunçu, Nizami, Suraxanı). Each stop: readable unique ID, Azerbaijani display name, lat/lon. Add a test that all stop IDs are unique and every route references existing stops."
- **Xülasə:** routes_data.py dayanacaq kataloqu (8-dən çox rayon üzrə 89 dayanacaq) və 25 marşrut (hər birində 8–11 dayanacaq, ortaq qovşaq identifikatorları) kimi yenidən quruldu, məlumatın sadələşdirildiyi qeyd olundu; sərnişin səhifəsinə marşrut axtarışı əlavə edildi; operator xəritəsində problemsiz marşrutlar boz göstərilir, problemli və seçilmiş marşrutlar vurğulanır, avtobuslar yalnız seçilmiş və xəbərdarlıqlı marşrutlar üçün görünür; ciddiliyə görə sıralanmış, axtarışlı marşrut siyahısı və cədvəl. Şəbəkə məlumatları üçün testlər əlavə edildi, 4 marşruta əsaslanan fərziyyələr yeniləndi.
- **Dəyişdirilmiş fayllar:** backend/app/routes_data.py, tests/test_routes_data.py, tests/test_api.py, tests/test_health.py, frontend/passenger.html, frontend/js/passenger.js, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 12:55
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Smart dispatch: when an anomaly alert is created, find a donor route with the most \"low\"/unknown density and at least 3 buses, and attach a recommendation to the alert: \"Marşrut X-dən 1 avtobusu Marşrut Y-ə yönləndirin\". Add POST /api/operator/alerts/{id}/dispatch that actually moves one bus in the simulator from donor to the target route and resolves the alert. Show the recommendation and a \"Təsdiqlə\" button in the operator alerts panel. Unit-test donor selection and the dispatch endpoint. Commit."
- **Xülasə:** dispatch.py əlavə edildi (aktiv xəbərdarlığı olmayan, ən azı 3 avtobusu olan sakit marşrutlar arasından donor seçimi; avtobusun xəbərdarlıqlı marşruta keçirilməsi); yeni xəbərdarlıqlarda tövsiyə saxlanılır (kiçik SQLite sütun miqrasiyası ilə), POST /api/operator/alerts/{id}/dispatch, operator panelində tövsiyə sətri və "Təsdiqlə" düyməsi; donor seçimi və yönləndirmə testləri.
- **Dəyişdirilmiş fayllar:** backend/app/dispatch.py, backend/app/anomaly.py, backend/app/store.py, backend/app/models.py, backend/app/main.py, frontend/js/operator.js, frontend/css/style.css, tests/test_dispatch.py, AI_DECLARATION.md

## 2026-10-31 13:02
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Two small fixes first:
- Move ANOMALY_WINDOW_SEC and other tunables into backend/app/config.py to break the anomaly -> dispatch -> density import loop.
- Avoid wrong Azerbaijani suffixes: change the recommendation text to \"Tövsiyə: Marşrut X → Marşrut Y (1 avtobus yönləndirin)\" and the dispatched text to \"Avtobus 30-3 → Marşrut H1\".
Then report trust (keep it simple, put logic in trust.py):
- Passenger page generates an anonymous client_id (localStorage) and sends it with reports.
- Rate limit: max 1 report per client per bus per 60s -> 429 with Azerbaijani message, shown as a toast.
- Optional lat/lon in the report: if given and more than 500 m from the bus, reject with 422 (\"Avtobusdan çox uzaqdasınız\"). Passenger page sends browser geolocation if allowed, otherwise skips.
- Time decay: in density, weight each report by freshness (linear from 1.0 now to 0 at window end) and expose a confidence score 0-1 per route based on number of unique clients and freshness. Show confidence as a small bar in the operator table.
- Demo flood uses distinct client_ids so it still works.
Unit-test the rate limit, distance check and weighting. Commit."
- **Xülasə:** Bütün parametrləri toplayan config.py əlavə edildi (idxal dövrəsi aradan qaldırıldı), yönləndirmə mətnləri şəkilçisiz formaya salındı. trust.py (sürət məhdudiyyəti, haversine ilə məsafə yoxlaması, təzəlik çəkisi, etibarlılıq), bildirişlərdə client_id/lat/lon (SQLite sütun miqrasiyası ilə), sıxlıqda çəkili əsas səviyyə və etibarlılıq, sərnişin tərəfində cihaz identifikatoru, geolokasiya və xəta mesajları, operator cədvəlində etibarlılıq zolağı; etibarlılıq üzrə modul və API testləri.
- **Dəyişdirilmiş fayllar:** backend/app/config.py, backend/app/trust.py, backend/app/density.py, backend/app/models.py, backend/app/store.py, backend/app/main.py, backend/app/anomaly.py, backend/app/dispatch.py, backend/app/simulator.py, backend/app/eta.py, frontend/js/passenger.js, frontend/js/operator.js, frontend/operator.html, frontend/css/style.css, tests/test_trust.py, tests/test_anomaly.py, tests/test_api.py, tests/test_dispatch.py, tests/test_eta.py, tests/test_health.py, tests/test_operator_api.py, tests/test_simulator.py, AI_DECLARATION.md

## 2026-10-31 13:07
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Passenger alternatives (logic in alternatives.py):
- In GET /api/stops/{stop_id}/eta, for each bus with density \"high\", add a suggestion: the next bus arriving at the same stop (same or any other route serving the stop) with density low/medium/unknown, with its eta and an extra-wait in minutes. Only suggest it if extra wait <= 10 minutes.
- Passenger ETA card: under a crowded bus show \"💡 Bu avtobus doludur. {route} {eta} dəq sonra gəlir (sıxlıq: Orta)\" in a highlighted box.
- Also add a stop-level \"Ən rahat seçim\" badge on the least crowded bus within the next 15 minutes.
Unit-test the suggestion rules (same route, other route, too long wait, no alternative). Commit."
- **Xülasə:** alternatives.py əlavə edildi (hər dolu avtobus üçün 10 dəqiqə ərzində onunla eyni vaxtda və ya ondan sonra gələn, "Yüksək" olmayan ən yaxın avtobus; 15 dəqiqə ərzində sıxlığı məlum olan ən sakit avtobus), ETA endpointinə suggestion/most_comfortable sahələri, sərnişinin ETA kartında vurğulanmış tövsiyə qutusu və "⭐ Ən rahat seçim" nişanı; modul və API testləri.
- **Dəyişdirilmiş fayllar:** backend/app/alternatives.py, backend/app/models.py, backend/app/config.py, backend/app/main.py, frontend/js/passenger.js, frontend/css/style.css, tests/test_alternatives.py, AI_DECLARATION.md

## 2026-10-31 13:14
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "1) Simulator realism: give each bus a random start offset along its route (seeded, deterministic in tests) so arrivals spread out instead of bunching.
2) Synthetic background reports (config SYNTHETIC_REPORTS=1 by default, off in tests): every 5s generate a few reports with a rush-hour pattern, so central routes (through 28-may, koroglu, genclik) trend toward high and outer routes stay low. Use distinct synthetic client_ids.
3) Forecast (logic in forecast.py, readable): per route, compute a density score (low=1, medium=2, high=3) over recent time buckets, fit a simple linear trend, and predict the score 15 minutes ahead. Return predicted level and trend (rising/stable/falling) in GET /api/operator/forecast.
4) Early warning: if a route is predicted \"high\" in 15 min but not high now, show a yellow \"⚠ Proqnoz: 15 dəq sonra Yüksək sıxlıq gözlənilir\" item in the operator alerts panel (not a real alert), and a trend arrow ↑ → ↓ column in the density table.
Unit-test the trend fit and predicted levels with fixed data. Commit."
- **Xülasə:** Simulyatorda marşrutlar üzrə toxumlu (seeded) təsadüfi başlanğıc sürüşmələri; mərkəzi marşrutlarda pik saat dalğası yaradan synthetic.py fon bildirişləri; forecast.py (birdəqiqəlik intervallar, ən kiçik kvadratlar trendi, 15 dəqiqəlik proqnoz, erkən xəbərdarlıq) və GET /api/operator/forecast; operator panelində erkən xəbərdarlıqlar və trend oxları; proqnoz, sintetik bildiriş və sürüşmə testləri.
- **Dəyişdirilmiş fayllar:** backend/app/config.py, backend/app/simulator.py, backend/app/synthetic.py, backend/app/forecast.py, backend/app/models.py, backend/app/main.py, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, tests/conftest.py, tests/test_forecast.py, tests/test_synthetic.py, AI_DECLARATION.md

## 2026-10-31 13:21
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "1) Performance: density/anomaly/forecast should query only reports within the needed time range (indexed SQL by route_id and timestamp), not full history.
2) Demo speed: add RUSH_PERIOD_MIN to config (default 30, demo 6) so early warnings appear within ~2 minutes in demo mode.
3) Analytics: GET /api/operator/analytics returns per-minute report counts by level for the last 30 minutes (whole network) and top 10 routes by weighted high share.
4) New operator section \"Analitika\" with Chart.js copied into frontend/vendor (no CDN): a stacked area chart of low/medium/high over time and a horizontal bar chart of the top 10 most crowded routes. Refresh every 10s, without re-creating charts (update data only).
5) Summary card \"Şəbəkə sıxlıq indeksi\" (0-100) on top.
Keep code readable. Test the analytics endpoint. Commit."
- **Xülasə:** SQLite indeksləri və zaman aralığı ilə məhdudlaşan sorğular (sıxlıq, 2 pəncərəlik geriyə baxışla anomaliya, proqnoz); RUSH_PERIOD_MIN; GET /api/operator/analytics ilə analytics.py (30 dəqiqəlik zaman xətti, ən sıx 10 marşrut, şəbəkə sıxlıq indeksi); layihəyə daxil edilmiş Chart.js 4.4.4 ilə operatorun "Analitika" bölməsi (yerində yenilənən yığılmış sahə və üfüqi zolaq qrafikləri, cədvəl görünüşü) və sıxlıq indeksi kartı; analitika və sorğu testləri.
- **Dəyişdirilmiş fayllar:** backend/app/store.py, backend/app/density.py, backend/app/anomaly.py, backend/app/forecast.py, backend/app/config.py, backend/app/synthetic.py, backend/app/analytics.py, backend/app/models.py, backend/app/main.py, frontend/operator.html, frontend/js/operator.js, frontend/css/style.css, frontend/vendor/chartjs/*, tests/test_analytics.py, tests/test_synthetic.py, AI_DECLARATION.md

## 2026-10-31 13:27
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Add real-time push with Server-Sent Events: GET /api/stream emits \"buses\" every 2s and \"alert\" immediately when an alert is created or resolved. Use it in passenger.js and operator.js via EventSource; if the stream fails, fall back automatically to the existing polling. Show a small \"Canlı\" / \"Polling\" indicator in the header. Keep it simple, test the stream endpoint briefly. Commit."
- **Xülasə:** events.py (axınlar üçün təhlükəsiz daxili yayım və keep-alive ilə SSE axını) və GET /api/stream əlavə edildi; simulyator hər addımdan sonra "buses", store isə xəbərdarlıq yarananda və həll olunanda "alert" hadisəsi yayır. Sərnişin və operator səhifələri polling rejiminə avtomatik keçidlə EventSource-dan istifadə edir, başlıqda Canlı/Polling göstəricisi var; sərnişin səhifəsi marşrutu tərk edən avtobusların markerlərini də silir. Axın testləri əlavə edildi.
- **Dəyişdirilmiş fayllar:** backend/app/events.py, backend/app/main.py, backend/app/store.py, backend/app/simulator.py, backend/app/config.py, frontend/passenger.html, frontend/operator.html, frontend/js/passenger.js, frontend/js/operator.js, frontend/css/style.css, tests/test_stream.py, AI_DECLARATION.md

## 2026-10-31 13:45
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "UI polish only, no backend changes, keep code readable:
1) Bus markers: small inline SVG bus icon (front view) as a Leaflet divIcon, body colored by density (green/orange/red/grey), route number label, subtle shadow. Rotate or not, keep it simple.
2) Passenger page: allow selecting up to 3 routes at once as removable chips; each selected route gets its own distinct line color; bus icons keep density colors with a thin border in the route color. Show stop dots only at zoom >= 14 (except selected stop).
3) Operator page: reorganize into tabs \"Xəritə\", \"Alertlər\", \"Analitika\". Keep summary cards always visible on top. Alert count badge on the Alertlər tab.
4) Visual cleanup across both pages: consistent spacing scale, one font (system-ui), max 3 accent colors plus density colors, rounded cards with light shadow, clear headings, empty states with short helpful text, nothing overlapping on 1366x768 and mobile width.
Update common.js/style.css rather than duplicating. Run pytest -q and commit."
- **Xülasə:** Hər iki səhifənin istifadə etdiyi js/common.js əlavə edildi (ortaq API, formatlama, toast, xəritə və canlı axın köməkçiləri, SVG avtobus ikonu və markerlərin sinxronlaşdırılması); sərnişin səhifəsi yoxlanılmış fərqli xətt rəngləri ilə 3 marşrut çipini, marşrut rəngində avtobus konturlarını və miqyasdan asılı dayanacaq nöqtələrini dəstəkləyir; operator səhifəsi xəbərdarlıq sayı nişanı ilə Xəritə/Alertlər/Analitika tablarına bölündü; style.css boşluq və şrift şkalası, bir şrift və 3 vurğu rəngi əsasında yenidən yazıldı, boş vəziyyət mətnləri əlavə edildi; giriş səhifəsi yeniləndi. Backend dəyişdirilməyib.
- **Dəyişdirilmiş fayllar:** frontend/js/common.js, frontend/js/passenger.js, frontend/js/operator.js, frontend/passenger.html, frontend/operator.html, frontend/index.html, frontend/css/style.css, AI_DECLARATION.md

## 2026-10-31 13:53
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Change the default of MAX_REPORT_DISTANCE_M in config.py to 0 (disabled), since GPS is simulated. Keep the feature: document in README/config that setting it to e.g. 500 enables the proximity check for real GPS. Update tests accordingly, run pytest -q and commit."
- **Xülasə:** Məsafə yoxlaması standart olaraq söndürüldü (MAX_REPORT_DISTANCE_M=0) və bu, config.py, trust.py və yeni README.md-də (işə salma, demo rejimi, parametrlər) izah edildi; məsafə testləri yoxlamanı açıq şəkildə aktivləşdirir, yeni testlər isə söndürülmüş standart vəziyyəti yoxlayır.
- **Dəyişdirilmiş fayllar:** backend/app/config.py, backend/app/trust.py, README.md, tests/test_trust.py, AI_DECLARATION.md

## 2026-10-31 14:03
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Two small UX fixes, no rule changes:
1) Passenger page: persist selected routes and selected stop in localStorage and restore them on load, so switching to Operator and back keeps the selection.
2) Operator page: for routes whose latest reports are \"high\" but no alert yet, show a pending indicator in the Alertlər tab and the route list: \"Yüksək sıxlıq izlənilir: 1/3 bildiriş, alertə qədər ~X san\". Expose this from the anomaly logic (count in current high run and seconds remaining to reach the window). Add a short help text: \"Alert üçün xətt ANOMALY_WINDOW_SEC ərzində ardıcıl Yüksək qalmalıdır\".
Test the pending calculation. Run pytest -q and commit."
- **Xülasə:** Sərnişinin seçimi (marşrutlar və dayanacaq) localStorage-da saxlanılır və yükləmə zamanı bərpa olunur. anomaly.py-a pending_status/pending əlavə edildi (qayda ilə eyni bildiriş pəncərəsi və "artıq həll olunub" yoxlaması; qaydanın özü dəyişməyib) və GET /api/operator/pending ilə təqdim olunur; operator panelində "izlənilir" elementləri, marşrut siyahısında ⏳ nişanları və real pəncərə dəyəri ilə qayda izahı göstərilir. "İzlənilir" hesablamasının modul və API testləri.
- **Dəyişdirilmiş fayllar:** backend/app/anomaly.py, backend/app/models.py, backend/app/main.py, frontend/js/passenger.js, frontend/js/operator.js, frontend/operator.html, frontend/css/style.css, tests/test_anomaly.py, tests/test_operator_api.py, AI_DECLARATION.md

## 2026-10-31 14:05
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Simulator tuning, config only where possible:
1) Slow buses down so movement on the map looks realistic: one stop-to-stop segment should take about 30s of real time instead of 10s, still moving smoothly every 2s. Adjust SIM_TIME_SCALE so displayed ETAs stay realistic (~2-3 min per segment) and remain consistent with the new speed.
2) Variable fleet size: central/busy routes (through 28-may, koroglu, genclik, nizami) get 4-5 buses, outer routes keep 3. Make it a per-route value in routes_data.py with the default from config.
Update tests that assume a fixed bus count or speed. Run pytest -q and commit."
- **Xülasə:** STEPS_PER_SEGMENT 5 → 15 (2 saniyəlik addımlarla seqment başına 30 s) və SIM_TIME_SCALE 15 → 5 (seqment yenə 2,5 dəqiqə kimi göstərilir). routes_data.py-da FLEET_SIZE ilə Route.bus_count (iki və daha çox qovşaqdan keçən marşrutlara 5, bir qovşaqdan keçənlərə 4, digərlərinə config-dəki standart 3 avtobus); simulyator bundan istifadə edir. Testlər avtobus sayını hər marşrutun öz dəyərindən götürür; yeni avtobus sayı və sürət testləri.
- **Dəyişdirilmiş fayllar:** backend/app/config.py, backend/app/eta.py, backend/app/models.py, backend/app/routes_data.py, backend/app/simulator.py, tests/test_api.py, tests/test_dispatch.py, tests/test_eta.py, tests/test_health.py, tests/test_operator_api.py, tests/test_routes_data.py, tests/test_simulator.py, tests/test_stream.py, AI_DECLARATION.md

## 2026-10-31 14:20
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Two operator page fixes, keep it small:
1) Slow load (~30s before routes appear): find the cause first (likely many sequential per-route requests, N+1 SQL queries, or SSE/polling blocking initial fetches). Fix it: add one GET /api/operator/overview that returns routes with geometry, density, pending, alerts and forecast in a single response with batched SQL; render the map from it immediately, then start SSE and polling. Target: page usable in under 2s. Report what the cause was.
2) Network overview: on load, fit the map to the central Baku bounds of all routes (not the whole region). Make non-problem routes visible but calm (thin grey, ~0.5 opacity instead of nearly invisible), problem routes thick and colored, and show a small \"Şəbəkə görünüşü\" button that resets the view.
Run pytest -q and commit."
- **Xülasə:** Əsas səbəb: ortaq SQLite bağlantısı sorğu axınları və fon tapşırıqları tərəfindən kilidsiz, paralel istifadə olunurdu; paralel sorğular uğursuz olurdu (20 yeniləmədən 13-ü) və səhifə uğurlu yeniləməyə qədər boş qalırdı; əlavə səbəb: Windows-da localhost hər yeni bağlantıya ~2 s əlavə edir (əvvəlcə IPv6 yoxlanılır). Kilidli store (_query/_write), toplu GET /api/operator/overview (hər yeniləmədə 199 əvəzinə 3 SQL sorğusu; ortaq saf funksiyalar sayəsində eyni nəticələr) və SSE/polling-dən əvvəl bir overview sorğusu ilə çəkilən operator səhifəsi ilə düzəldildi. Şəbəkə görünüşü mərkəzi 5–95 faizlik sərhədlərə uyğunlaşdırılır, problemsiz marşrutlar 0,5 şəffaflıqla göstərilir, "Şəbəkə görünüşü" düyməsi əlavə edildi. Overview və paralel istifadə testləri; README-də 127.0.0.1 qeydi.
- **Dəyişdirilmiş fayllar:** backend/app/store.py, backend/app/overview.py, backend/app/density.py, backend/app/forecast.py, backend/app/anomaly.py, backend/app/models.py, backend/app/main.py, frontend/js/operator.js, frontend/css/style.css, tests/test_overview.py, README.md, AI_DECLARATION.md

## 2026-10-31 14:30
- **Alət:** Claude Code
- **Prompt (orijinal, ingilis dilində):** "Final submission package, no new features:
1) dispatch.py tie-break: prefer donor routes not passing a hub, then more buses.
2) tests/test_integration.py: full flow report -> density -> alert -> dispatch -> resolved.
3) Dockerfile (python:3.12-slim, uvicorn 0.0.0.0:8000), docker-compose.yml with env vars + volume for data.db, .env.demo, run_demo.ps1 (Windows, starts from backend/).
4) Expand README.md (keep existing): Azerbaijani summary on top, features, screenshots placeholders docs/screenshots/*.png, run locally (http://127.0.0.1:8000) / Docker / tests, demo script for judges, Mermaid architecture diagram, API table, limitations, team roles (Ülvi Mustafayev - Backend & API; Anar Hümmətli - Frontend & UI/UX; Xizri Saxrayev - AI integration, testing & documentation).
5) docs/TEXNIKI_IZAH.md in formal Azerbaijani: problem context, solution, architecture and data flow, technologies and why, project structure, key algorithms (ETA, anomaly rule, smart dispatch, report trust/confidence, forecast, alternatives), testing approach and results, the SQLite concurrency bug found and fixed, limitations, future development (real BakuBus GPS/GTFS, BakuCard data, mobile app, ML forecasting, PostgreSQL, auth).
6) AI_DECLARATION_AZ.md: Azerbaijani version of AI_DECLARATION.md with a summary of tools used (Claude Code in VS Code for code/tests/docs, Claude for planning and prompt design), how and for which parts, keeping every prompt in original English.
Run pytest -q and commit."
- **Xülasə:** Yönləndirmədə bərabərlik halında heç bir qovşaqdan keçməyən donor marşrutlara, sonra daha çox avtobusu olanlara üstünlük verilir (config-də HUB_STOP_IDS); tam inteqrasiya testi; Dockerfile, docker-compose.yml, .env.demo, run_demo.ps1; genişləndirilmiş README (Azərbaycan dilində xülasə, imkanlar, ekran görüntüsü yerləri, lokal/Docker/test işə salma, münsiflər üçün demo ssenarisi, Mermaid arxitektura diaqramı, API cədvəli, məhdudiyyətlər, komanda); docs/TEXNIKI_IZAH.md; AI_DECLARATION_AZ.md. AI_DECLARATION.md-dəki bütün əvvəlki qeydlərin vaxtı real commit vaxtlarına uyğun düzəldildi (əvvəllər təxmini idi).
- **Dəyişdirilmiş fayllar:** backend/app/dispatch.py, backend/app/config.py, tests/test_dispatch.py, tests/test_integration.py, Dockerfile, .dockerignore, docker-compose.yml, .env.demo, run_demo.ps1, README.md, docs/screenshots/README.md, docs/TEXNIKI_IZAH.md, AI_DECLARATION.md, AI_DECLARATION_AZ.md
