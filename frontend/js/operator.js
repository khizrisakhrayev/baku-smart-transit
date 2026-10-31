// Operator dashboard: route density map, density table, alerts and demo controls.

const POLL_MS = 3000;
const BAKU_CENTER = [40.395, 49.88];
const DENSITY_LABELS = { low: "Aşağı", medium: "Orta", high: "Yüksək" };
const DENSITY_COLORS = { low: "#22a06b", medium: "#f59e0b", high: "#e5484d" };
const UNKNOWN_COLOR = "#8a94a6";

const state = {
  routes: {},           // route id -> route
  routeLines: {},       // route id -> Leaflet polyline
  busMarkers: {},       // bus id -> Leaflet marker
  knownAlertIds: null,  // ids seen so far; null until the first load
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
    state.routeLines[route.id] = L.polyline(points, { color: UNKNOWN_COLOR, weight: 6, opacity: 0.8 })
      .bindTooltip(`Marşrut ${route.id}: ${route.name}`, { sticky: true })
      .addTo(map);
    for (const stop of route.stops) {
      L.circleMarker([stop.lat, stop.lon], { radius: 4, color: "#1c2333", weight: 2, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(stop.name)
        .addTo(map);
    }
  }
  map.fitBounds(allPoints, { padding: [30, 30] });
}

function colorRouteLines(densities) {
  for (const d of densities) {
    const line = state.routeLines[d.route_id];
    if (line) line.setStyle({ color: DENSITY_COLORS[d.dominant_level] || UNKNOWN_COLOR });
  }
}

// --- Live buses ---

function busIcon(bus) {
  return L.divIcon({
    className: "bus-icon",
    html: `<div class="bus-marker ${densityClass(bus.density)}">${bus.route_id}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

function updateBusMarkers(buses) {
  for (const bus of buses) {
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
}

// --- Summary, table and alerts ---

function renderSummary(buses, densities, alerts) {
  const reports = densities.reduce((sum, d) => sum + d.counts.low + d.counts.medium + d.counts.high, 0);
  document.getElementById("stat-buses").textContent = buses.length;
  document.getElementById("stat-reports").textContent = reports;
  document.getElementById("stat-alerts").textContent = alerts.filter((a) => !a.resolved_at).length;
}

function renderDensityTable(densities) {
  document.getElementById("density-body").innerHTML = densities.map((d) => `
    <tr>
      <td><span class="route-tag">${d.route_id}</span> ${d.route_name}</td>
      <td>${d.bus_count}</td>
      <td>${d.counts.low}</td>
      <td>${d.counts.medium}</td>
      <td>${d.counts.high}</td>
      <td>${badge(d.dominant_level)}</td>
      <td>${formatTime(d.last_report_at)}</td>
      <td><button class="btn-small" data-demo-route="${d.route_id}">Demo</button></td>
    </tr>`).join("");
}

function renderAlerts(alerts) {
  const list = document.getElementById("alert-list");
  if (!alerts.length) {
    list.innerHTML = '<li class="hint">Xəbərdarlıq yoxdur</li>';
    return;
  }
  list.innerHTML = alerts.map((a) => `
    <li class="alert-item ${a.resolved_at ? "resolved" : "active"}">
      <div class="alert-head">
        <strong>Marşrut ${routeLabel(a.route_id)}</strong>
        ${a.resolved_at ? "" : `<button class="btn-small btn-resolve" data-resolve-id="${a.id}">Həll edildi</button>`}
      </div>
      <div>${a.message}</div>
      <div class="hint">
        Yaradıldı: ${formatTime(a.created_at)}
        ${a.resolved_at ? ` · Həll edildi: ${formatTime(a.resolved_at)}` : ""}
      </div>
    </li>`).join("");
}

// --- Polling ---

async function refresh() {
  const [buses, densities, alerts] = await Promise.all([
    api("/api/buses"),
    api("/api/operator/density"),
    api("/api/operator/alerts"),
  ]);
  updateBusMarkers(buses);
  colorRouteLines(densities);
  renderSummary(buses, densities, alerts);
  renderDensityTable(densities);
  renderAlerts(alerts);
  notifyNewAlerts(alerts);
}

// --- Actions (buttons are re-rendered on each poll, so listen on the containers) ---

document.getElementById("alert-list").addEventListener("click", async (event) => {
  const id = event.target.dataset.resolveId;
  if (!id) return;
  await api(`/api/operator/alerts/${id}/resolve`, { method: "POST" });
  showToast("Xəbərdarlıq həll edildi");
  refresh();
});

document.getElementById("density-body").addEventListener("click", async (event) => {
  const routeId = event.target.dataset.demoRoute;
  if (!routeId) return;
  await api(`/api/demo/flood-high?route_id=${encodeURIComponent(routeId)}`, { method: "POST" });
  showToast(`Demo: Marşrut ${routeId} üçün "Yüksək" bildirişlər göndərildi`);
  refresh();
});

loadRoutes().then(refresh).catch(console.error);
setInterval(() => refresh().catch(console.error), POLL_MS);
