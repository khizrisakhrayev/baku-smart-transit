// Operator dashboard: route density map, route list, density table, alerts and demo controls.
//
// With 25 routes the map stays readable by only emphasising what matters:
// - every route is a thin grey line;
// - routes with medium/high density or an active alert are thick and colored;
// - the selected route is thick, shows its stops and is zoomed to;
// - bus markers are shown only for the selected route and alerted routes.

const POLL_MS = 3000;
const BAKU_CENTER = [40.41, 49.89];
const DENSITY_LABELS = { low: "Aşağı", medium: "Orta", high: "Yüksək" };
const DENSITY_COLORS = { low: "#22a06b", medium: "#f59e0b", high: "#e5484d" };
const SELECTED_COLOR = "#2563eb";
const IDLE_COLOR = "#8a94a6";
const SEVERITY = { high: 3, medium: 2, low: 1 }; // alerts rank above all (4), no data is 0

const state = {
  routes: {},             // route id -> route
  routeLines: {},         // route id -> Leaflet polyline
  busMarkers: {},         // bus id -> Leaflet marker
  stopLayer: null,        // stop markers of the selected route
  selectedRouteId: null,
  densities: [],          // last /api/operator/density response
  alertRouteIds: new Set(),  // routes with an active alert
  knownAlertIds: null,    // alert ids seen so far; null until the first load
  forecasts: {},          // route id -> /api/operator/forecast entry
  buses: [],              // latest bus positions (from the live stream or polling)
  live: false,            // true while the live stream is connected
};

// --- Map setup ---

const map = L.map("map").setView(BAKU_CENTER, 12);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

// --- Helpers ---

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
}

function densityClass(level) {
  return `density-${level || "unknown"}`;
}

function densityLabel(level) {
  return DENSITY_LABELS[level] || "Məlum deyil";
}

function badge(level) {
  return `<span class="badge ${densityClass(level)}">${densityLabel(level)}</span>`;
}

function formatTime(isoText) {
  if (!isoText) return "—";
  return new Date(isoText).toLocaleTimeString("az-AZ", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function routeLabel(routeId) {
  const route = state.routes[routeId];
  return route ? `${route.id} · ${route.name}` : routeId;
}

function showToast(text) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("visible"), 4000);
}

// --- Severity: alert > high > medium > low > no data ---

function severity(density) {
  if (state.alertRouteIds.has(density.route_id)) return 4;
  return SEVERITY[density.dominant_level] || 0;
}

function bySeverity(a, b) {
  return severity(b) - severity(a)
    || b.counts.high - a.counts.high
    || a.route_id.localeCompare(b.route_id, undefined, { numeric: true });
}

function isProblem(density) {
  return severity(density) >= 2;
}

// --- New-alert signal: short beep + flashing alerts panel ---

function beep() {
  try {
    const audio = new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.2, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.5);
    osc.connect(gain).connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + 0.5);
  } catch (error) {
    // Browsers may block audio before the first click; the flash and toast still show.
  }
}

function flashAlerts() {
  const card = document.getElementById("alerts-card");
  card.classList.remove("flash");
  void card.offsetWidth; // restart the CSS animation
  card.classList.add("flash");
}

function notifyNewAlerts(alerts) {
  const activeIds = alerts.filter((a) => !a.resolved_at).map((a) => a.id);
  if (state.knownAlertIds === null) {
    state.knownAlertIds = new Set(activeIds); // first load: don't alarm for old alerts
    return;
  }
  const fresh = alerts.filter((a) => !a.resolved_at && !state.knownAlertIds.has(a.id));
  fresh.forEach((a) => state.knownAlertIds.add(a.id));
  if (fresh.length) {
    showToast(`⚠ Yeni xəbərdarlıq: Marşrut ${fresh.map((a) => a.route_id).join(", ")}`);
    beep();
    flashAlerts();
  }
}

// --- Routes on the map ---

async function loadRoutes() {
  const routes = await api("/api/routes");
  const allPoints = [];
  for (const route of routes) {
    state.routes[route.id] = route;
    const points = route.stops.map((s) => [s.lat, s.lon]);
    allPoints.push(...points);
    state.routeLines[route.id] = L.polyline(points, { color: IDLE_COLOR, weight: 3, opacity: 0.35 })
      .bindTooltip(`Marşrut ${route.id}: ${route.name}`, { sticky: true })
      .on("click", () => selectRoute(route.id))
      .addTo(map);
  }
  map.fitBounds(allPoints, { padding: [30, 30] });
}

function styleRouteLines() {
  for (const d of state.densities) {
    const line = state.routeLines[d.route_id];
    if (!line) continue;
    const selected = d.route_id === state.selectedRouteId;
    const alerted = state.alertRouteIds.has(d.route_id);
    if (selected || isProblem(d)) {
      const color = alerted ? DENSITY_COLORS.high : DENSITY_COLORS[d.dominant_level] || SELECTED_COLOR;
      line.setStyle({ color, weight: selected ? 8 : 6, opacity: 0.9 });
      line.bringToFront();
    } else {
      line.setStyle({ color: IDLE_COLOR, weight: 3, opacity: 0.35 });
    }
  }
  // Keep the selected route on top of other highlighted routes.
  if (state.selectedRouteId) state.routeLines[state.selectedRouteId].bringToFront();
}

function selectRoute(routeId) {
  state.selectedRouteId = state.selectedRouteId === routeId ? null : routeId; // click again to deselect
  if (state.stopLayer) state.stopLayer.remove();
  state.stopLayer = null;
  if (state.selectedRouteId) {
    const route = state.routes[routeId];
    state.stopLayer = L.layerGroup(route.stops.map((stop) =>
      L.circleMarker([stop.lat, stop.lon], { radius: 5, color: "#1c2333", weight: 2, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(stop.name)
    )).addTo(map);
    map.fitBounds(state.routeLines[routeId].getBounds(), { padding: [40, 40] });
  }
  styleRouteLines();
  renderRouteList();
  refresh().catch(console.error); // update bus markers right away
}

// --- Live buses (selected + alerted routes only) ---

function busIcon(bus) {
  return L.divIcon({
    className: "bus-icon",
    html: `<div class="bus-marker ${densityClass(bus.density)}">${bus.route_id}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

function isBusVisible(bus) {
  return bus.route_id === state.selectedRouteId || state.alertRouteIds.has(bus.route_id);
}

function updateBusMarkers(buses) {
  const visibleIds = new Set();
  for (const bus of buses.filter(isBusVisible)) {
    visibleIds.add(bus.id);
    let marker = state.busMarkers[bus.id];
    if (!marker) {
      marker = L.marker([bus.lat, bus.lon], { icon: busIcon(bus), zIndexOffset: 1000 })
        .bindTooltip(`Avtobus ${bus.id}`)
        .addTo(map);
      state.busMarkers[bus.id] = marker;
    } else if (marker.bus.density !== bus.density) {
      marker.setIcon(busIcon(bus)); // only recolor when needed, so the glide animation survives
    }
    marker.bus = bus;
    marker.setLatLng([bus.lat, bus.lon]);
  }
  for (const [id, marker] of Object.entries(state.busMarkers)) {
    if (!visibleIds.has(id)) {
      marker.remove();
      delete state.busMarkers[id];
    }
  }
}

// --- Summary, route list, table and alerts ---

function renderSummary(buses, alerts) {
  const reports = state.densities.reduce((sum, d) => sum + d.counts.low + d.counts.medium + d.counts.high, 0);
  document.getElementById("stat-buses").textContent = buses.length;
  document.getElementById("stat-reports").textContent = reports;
  document.getElementById("stat-alerts").textContent = alerts.filter((a) => !a.resolved_at).length;
}

// Search matches the route number, route name or any of its stop names.
function routeMatches(route, query) {
  const text = [route.id, route.name, ...route.stops.map((s) => s.name)].join(" ");
  return text.toLocaleLowerCase("az").includes(query);
}

function renderRouteList() {
  const query = document.getElementById("route-search").value.trim().toLocaleLowerCase("az");
  const rows = [...state.densities].sort(bySeverity)
    .filter((d) => routeMatches(state.routes[d.route_id], query));
  const list = document.getElementById("route-list");
  if (!rows.length) {
    list.innerHTML = '<li class="hint">Heç nə tapılmadı</li>';
    return;
  }
  list.innerHTML = rows.map((d) => `
    <li class="route-item ${d.route_id === state.selectedRouteId ? "selected" : ""}" data-route-id="${d.route_id}">
      <span class="route-tag ${densityClass(d.dominant_level)}">${d.route_id}</span>
      <span class="route-name">${d.route_name}</span>
      ${state.alertRouteIds.has(d.route_id) ? '<span class="alert-icon" title="Aktiv xəbərdarlıq">⚠</span>' : ""}
      ${badge(d.dominant_level)}
    </li>`).join("");
}

// Small bar + percentage for the route's confidence score (0-1).
function confidenceBar(value) {
  const percent = Math.round(value * 100);
  return `
    <div class="confidence" title="Unikal bildirişçilər və təzəlik əsasında">
      <div class="confidence-track"><div class="confidence-fill" style="width: ${percent}%"></div></div>
      <span>${percent}%</span>
    </div>`;
}

function renderDensityTable() {
  const rows = [...state.densities].sort(bySeverity);
  document.getElementById("density-body").innerHTML = rows.map((d) => `
    <tr class="${state.alertRouteIds.has(d.route_id) ? "row-alert" : ""}">
      <td>
        <span class="route-tag">${d.route_id}</span> ${d.route_name}
        ${state.alertRouteIds.has(d.route_id) ? '<span class="alert-icon" title="Aktiv xəbərdarlıq">⚠</span>' : ""}
      </td>
      <td>${d.bus_count}</td>
      <td>${d.counts.low}</td>
      <td>${d.counts.medium}</td>
      <td>${d.counts.high}</td>
      <td>${badge(d.dominant_level)}</td>
      <td>${trendArrow(state.forecasts[d.route_id])}</td>
      <td>${confidenceBar(d.confidence)}</td>
      <td>${formatTime(d.last_report_at)}</td>
      <td><button class="btn-small" data-demo-route="${d.route_id}">Demo</button></td>
    </tr>`).join("");
}

// Smart-dispatch recommendation (active alert) or what was dispatched (resolved alert).
function dispatchLine(alert) {
  if (alert.dispatched_bus_id) {
    return `<div class="dispatch done">🚌 Avtobus ${alert.dispatched_bus_id} → Marşrut ${alert.route_id}</div>`;
  }
  if (alert.resolved_at) return "";
  if (!alert.recommendation) {
    return '<div class="dispatch">Boş avtobusu olan donor marşrut tapılmadı</div>';
  }
  return `
    <div class="dispatch">
      <span>💡 ${alert.recommendation}</span>
      <button class="btn-small btn-dispatch" data-dispatch-id="${alert.id}">Təsdiqlə</button>
    </div>`;
}

// Trend arrow for the density table, with the 15-minute prediction as a tooltip.
const TREND_ARROWS = { rising: "↑", stable: "→", falling: "↓" };

function trendArrow(forecast) {
  if (!forecast || !forecast.predicted_level) return '<span class="trend">—</span>';
  const title = `15 dəq sonra: ${densityLabel(forecast.predicted_level)}`;
  return `<span class="trend trend-${forecast.trend}" title="${title}">${TREND_ARROWS[forecast.trend]}</span>`;
}

// Early warnings: routes predicted "high" in 15 min but not high now. Not real alerts.
function warningItems() {
  return Object.values(state.forecasts)
    .filter((f) => f.early_warning && !state.alertRouteIds.has(f.route_id))
    .map((f) => `
      <li class="alert-item warning">
        <strong>Marşrut ${routeLabel(f.route_id)}</strong>
        <div>⚠ Proqnoz: 15 dəq sonra Yüksək sıxlıq gözlənilir</div>
      </li>`)
    .join("");
}

function renderAlerts(alerts) {
  const list = document.getElementById("alert-list");
  const warnings = warningItems();
  if (!alerts.length && !warnings) {
    list.innerHTML = '<li class="hint">Xəbərdarlıq yoxdur</li>';
    return;
  }
  const active = alerts.filter((a) => !a.resolved_at);
  const resolved = alerts.filter((a) => a.resolved_at);
  list.innerHTML = alertItems(active) + warnings + alertItems(resolved);
}

function alertItems(alerts) {
  return alerts.map((a) => `
    <li class="alert-item ${a.resolved_at ? "resolved" : "active"}">
      <div class="alert-head">
        <strong>Marşrut ${routeLabel(a.route_id)}</strong>
        ${a.resolved_at ? "" : `<button class="btn-small btn-resolve" data-resolve-id="${a.id}">Həll edildi</button>`}
      </div>
      <div>${a.message}</div>
      ${dispatchLine(a)}
      <div class="hint">
        Yaradıldı: ${formatTime(a.created_at)}
        ${a.resolved_at ? ` · Həll edildi: ${formatTime(a.resolved_at)}` : ""}
      </div>
    </li>`).join("");
}

// --- Analytics (Chart.js): charts are created once, then only their data is updated ---

const ANALYTICS_MS = 10000;
const LEVELS = ["low", "medium", "high"];
const TEXT_COLOR = "#1c2333";
const MUTED_COLOR = "#6b7489";
const GRID_COLOR = "#e3e7ef";

Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
Chart.defaults.color = MUTED_COLOR;

const charts = { timeline: null, topRoutes: null, topRouteNames: [] };

function withAlpha(hex, alpha) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

function shorten(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

// Writes each bar's value just past its tip (bars carry their value at the tip).
const barTipLabels = {
  id: "barTipLabels",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save();
    ctx.fillStyle = TEXT_COLOR;
    ctx.font = `12px ${Chart.defaults.font.family}`;
    ctx.textBaseline = "middle";
    chart.getDatasetMeta(0).data.forEach((bar, i) => {
      ctx.fillText(`${chart.data.datasets[0].data[i]}%`, bar.x + 6, bar.y);
    });
    ctx.restore();
  },
};

function createCharts() {
  // Stacked area: low at the bottom, high on top; each band fills down to the one below.
  charts.timeline = new Chart(document.getElementById("timeline-chart"), {
    type: "line",
    data: {
      labels: [],
      datasets: LEVELS.map((level, i) => ({
        label: DENSITY_LABELS[level],
        data: [],
        borderColor: DENSITY_COLORS[level],
        backgroundColor: withAlpha(DENSITY_COLORS[level], 0.15),
        fill: i === 0 ? "origin" : "-1",
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0 } },
        y: {
          stacked: true,
          beginAtZero: true,
          grid: { color: GRID_COLOR },
          border: { display: false },
          ticks: { precision: 0 },
          title: { display: true, text: "Bildiriş / dəq" },
        },
      },
      plugins: {
        legend: { position: "top", align: "start", labels: { color: TEXT_COLOR, boxWidth: 12, boxHeight: 12 } },
      },
    },
  });

  charts.topRoutes = new Chart(document.getElementById("top-routes-chart"), {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: "Yüksək payı",
        data: [],
        backgroundColor: DENSITY_COLORS.high,
        borderRadius: 4,
        borderSkipped: "start", // rounded at the data end, square at the baseline
        maxBarThickness: 24,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      layout: { padding: { right: 40 } }, // room for the tip labels
      scales: {
        x: { min: 0, max: 100, grid: { color: GRID_COLOR }, border: { display: false },
             ticks: { callback: (v) => `${v}%` } },
        y: { grid: { display: false }, ticks: { color: TEXT_COLOR } },
      },
      plugins: {
        legend: { display: false }, // one series: the caption names it
        tooltip: {
          callbacks: {
            title: (items) => charts.topRouteNames[items[0].dataIndex],
            label: (item) => `Yüksək payı: ${item.parsed.x}%`,
          },
        },
      },
    },
    plugins: [barTipLabels],
  });
}

function minuteLabel(isoText) {
  return new Date(isoText).toLocaleTimeString("az-AZ", { hour: "2-digit", minute: "2-digit" });
}

function updateTimelineChart(timeline) {
  charts.timeline.data.labels = timeline.map((m) => minuteLabel(m.minute));
  LEVELS.forEach((level, i) => {
    charts.timeline.data.datasets[i].data = timeline.map((m) => m[level]);
  });
  charts.timeline.update("none");
}

function updateTopRoutesChart(topRoutes) {
  charts.topRouteNames = topRoutes.map((r) => `Marşrut ${r.route_id} · ${r.route_name}`);
  charts.topRoutes.data.labels = topRoutes.map((r) => `${r.route_id} · ${shorten(r.route_name, 22)}`);
  charts.topRoutes.data.datasets[0].data = topRoutes.map((r) => Math.round(r.high_share * 100));
  charts.topRoutes.update("none");
  document.getElementById("top-routes-empty").hidden = topRoutes.length > 0;
}

function indexLevel(index) {
  if (index < 34) return "low";
  if (index < 67) return "medium";
  return "high";
}

function renderDensityIndex(index) {
  document.getElementById("stat-index").textContent = index ?? "–";
  document.getElementById("stat-index-level").innerHTML = index === null ? "" : badge(indexLevel(index));
}

// Table view: the same numbers as the charts, readable without color or hover.
function renderAnalyticsTables(data) {
  document.getElementById("top-routes-table").innerHTML = data.top_routes.length
    ? data.top_routes.map((r) => `
        <tr><td><span class="route-tag">${r.route_id}</span> ${r.route_name}</td>
            <td>${Math.round(r.high_share * 100)}%</td></tr>`).join("")
    : '<tr><td colspan="2" class="hint">Məlumat yoxdur</td></tr>';
  document.getElementById("timeline-table").innerHTML = [...data.timeline].reverse().map((m) => `
    <tr><td>${minuteLabel(m.minute)}</td><td>${m.low}</td><td>${m.medium}</td><td>${m.high}</td></tr>`).join("");
}

async function refreshAnalytics() {
  const data = await api("/api/operator/analytics");
  updateTimelineChart(data.timeline);
  updateTopRoutesChart(data.top_routes);
  renderDensityIndex(data.density_index);
  renderAnalyticsTables(data);
}

// --- Polling ---

async function refresh() {
  const [buses, densities, alerts, forecasts] = await Promise.all([
    state.live ? state.buses : api("/api/buses"), // pushed by the stream while live
    api("/api/operator/density"),
    api("/api/operator/alerts"),
    api("/api/operator/forecast"),
  ]);
  state.buses = buses;
  state.densities = densities;
  state.forecasts = Object.fromEntries(forecasts.map((f) => [f.route_id, f]));
  state.alertRouteIds = new Set(alerts.filter((a) => !a.resolved_at).map((a) => a.route_id));
  updateBusMarkers(buses);
  styleRouteLines();
  renderSummary(buses, alerts);
  renderRouteList();
  renderDensityTable();
  renderAlerts(alerts);
  notifyNewAlerts(alerts);
}

// --- Actions (lists are re-rendered on each poll, so listen on the containers) ---

document.getElementById("route-search").addEventListener("input", renderRouteList);

document.getElementById("route-list").addEventListener("click", (event) => {
  const item = event.target.closest("[data-route-id]");
  if (item) selectRoute(item.dataset.routeId);
});

document.getElementById("alert-list").addEventListener("click", async (event) => {
  const { resolveId, dispatchId } = event.target.dataset;
  if (resolveId) {
    await api(`/api/operator/alerts/${resolveId}/resolve`, { method: "POST" });
    showToast("Xəbərdarlıq həll edildi");
  } else if (dispatchId) {
    try {
      const result = await api(`/api/operator/alerts/${dispatchId}/dispatch`, { method: "POST" });
      showToast(`Avtobus ${result.bus.id} → Marşrut ${result.bus.route_id}`);
    } catch (error) {
      showToast("Yönləndirmə mümkün olmadı, marşrut vəziyyəti dəyişib");
    }
  } else {
    return;
  }
  refresh();
});

document.getElementById("density-body").addEventListener("click", async (event) => {
  const routeId = event.target.dataset.demoRoute;
  if (!routeId) return;
  await api(`/api/demo/flood-high?route_id=${encodeURIComponent(routeId)}`, { method: "POST" });
  showToast(`Demo: Marşrut ${routeId} üçün "Yüksək" bildirişlər göndərildi`);
  refresh();
});

// --- Live updates: Server-Sent Events, with polling as the automatic fallback ---

function setLive(live) {
  state.live = live;
  const indicator = document.getElementById("live-indicator");
  indicator.textContent = live ? "Canlı" : "Polling";
  indicator.classList.toggle("live", live);
}

// While the stream is open, bus positions arrive by push; on any error we drop back to
// polling (EventSource keeps retrying by itself and we switch back when it reconnects).
function startLiveStream(handlers) {
  if (!window.EventSource) return;
  const source = new EventSource("/api/stream");
  source.addEventListener("open", () => setLive(true));
  source.addEventListener("error", () => setLive(false));
  for (const [event, handle] of Object.entries(handlers)) {
    source.addEventListener(event, (message) => handle(JSON.parse(message.data)));
  }
}

function onLiveBuses(buses) {
  state.buses = buses;
  updateBusMarkers(buses);
  document.getElementById("stat-buses").textContent = buses.length;
}

loadRoutes().then(refresh).catch(console.error);
// Alerts are pushed the moment they change; refresh() then shows them (toast, beep, flash).
startLiveStream({ buses: onLiveBuses, alert: () => refresh().catch(console.error) });
setInterval(() => refresh().catch(console.error), POLL_MS);

createCharts();
refreshAnalytics().catch(console.error);
setInterval(() => refreshAnalytics().catch(console.error), ANALYTICS_MS);
