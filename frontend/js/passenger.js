// Passenger view: live bus map, stop ETAs and crowd density reporting.

const POLL_MS = 3000;
const BAKU_CENTER = [40.395, 49.86];
const ROUTE_COLOR = "#2563eb";
const DENSITY_LABELS = { low: "Aşağı", medium: "Orta", high: "Yüksək" };

const state = {
  routes: {},        // route id -> route (with stops)
  routeId: null,     // selected route
  stop: null,        // stop whose ETAs are shown
  bus: null,         // bus whose report panel is open
  routeLayer: null,  // polyline + stop markers of the selected route
  busMarkers: {},    // bus id -> Leaflet marker
};

// --- Map setup ---

const map = L.map("map", { zoomControl: false }).setView(BAKU_CENTER, 13);
L.control.zoom({ position: "bottomright" }).addTo(map);
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

function formatMinutes(minutes) {
  if (minutes < 1) return "1 dəq-dən az";
  return `${Math.round(minutes)} dəq`;
}

function show(id) { document.getElementById(id).hidden = false; }
function hide(id) { document.getElementById(id).hidden = true; }

function showToast(text) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("visible"), 3000);
}

// --- Routes and stops ---

async function loadRoutes() {
  const routes = await api("/api/routes");
  const select = document.getElementById("route-select");
  for (const route of routes) {
    state.routes[route.id] = route;
    select.add(new Option(`${route.id} · ${route.name}`, route.id));
  }
  select.addEventListener("change", () => selectRoute(select.value));
  selectRoute(routes[0].id);
}

function selectRoute(routeId) {
  state.routeId = routeId;
  state.stop = null;
  state.bus = null;
  hide("eta-card");
  hide("bus-panel");
  drawRoute(state.routes[routeId]);
  renderStopList(state.routes[routeId]);
  clearBusMarkers();
  refreshBuses();
}

function drawRoute(route) {
  if (state.routeLayer) state.routeLayer.remove();
  const points = route.stops.map((s) => [s.lat, s.lon]);
  const line = L.polyline(points, { color: ROUTE_COLOR, weight: 5, opacity: 0.7 });
  const stopMarkers = route.stops.map((stop) =>
    L.circleMarker([stop.lat, stop.lon], {
      radius: 7, color: ROUTE_COLOR, weight: 3, fillColor: "#fff", fillOpacity: 1,
    })
      .bindTooltip(stop.name)
      .on("click", () => showStop(stop))
  );
  state.routeLayer = L.layerGroup([line, ...stopMarkers]).addTo(map);
  map.fitBounds(line.getBounds(), { padding: [40, 40] });
}

function renderStopList(route) {
  const list = document.getElementById("stop-list");
  list.innerHTML = "";
  for (const stop of route.stops) {
    const item = document.createElement("li");
    item.textContent = stop.name;
    item.dataset.stopId = stop.id;
    item.addEventListener("click", () => {
      map.panTo([stop.lat, stop.lon]);
      showStop(stop);
    });
    list.appendChild(item);
  }
}

// --- Stop ETAs ---

function showStop(stop) {
  state.stop = stop;
  document.getElementById("eta-title").textContent = stop.name;
  document.querySelectorAll("#stop-list li").forEach((li) =>
    li.classList.toggle("active", li.dataset.stopId === stop.id)
  );
  show("eta-card");
  refreshEta();
}

async function refreshEta() {
  if (!state.stop) return;
  const etas = await api(`/api/stops/${state.stop.id}/eta`);
  const list = document.getElementById("eta-list");
  list.innerHTML = etas.length ? "" : '<li class="hint">Yaxınlaşan avtobus yoxdur</li>';
  for (const eta of etas) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="route-tag">${eta.route_id}</span>
      <span class="eta-bus">Avtobus ${eta.bus_id}</span>
      <span class="badge ${densityClass(eta.density)}">${densityLabel(eta.density)}</span>
      <strong class="eta-time">${formatMinutes(eta.eta_minutes)}</strong>`;
    list.appendChild(item);
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

function clearBusMarkers() {
  Object.values(state.busMarkers).forEach((marker) => marker.remove());
  state.busMarkers = {};
}

async function refreshBuses() {
  const routeId = state.routeId;
  const buses = await api(`/api/buses?route_id=${encodeURIComponent(routeId)}`);
  if (routeId !== state.routeId) return; // route changed while loading
  for (const bus of buses) {
    let marker = state.busMarkers[bus.id];
    if (!marker) {
      marker = L.marker([bus.lat, bus.lon], { icon: busIcon(bus), zIndexOffset: 1000 }).addTo(map);
      marker.on("click", () => openBusPanel(marker.bus));
      state.busMarkers[bus.id] = marker;
    } else if (marker.bus.density !== bus.density) {
      marker.setIcon(busIcon(bus)); // only recolor when needed, so the glide animation survives
    }
    marker.bus = bus;
    marker.setLatLng([bus.lat, bus.lon]);
    if (state.bus && state.bus.id === bus.id) renderBusPanel(bus);
  }
}

// --- Density reporting ---

function openBusPanel(bus) {
  state.bus = bus;
  renderBusPanel(bus);
  show("bus-panel");
}

function renderBusPanel(bus) {
  state.bus = bus;
  document.getElementById("bus-title").textContent = `Avtobus ${bus.id}`;
  const badge = document.getElementById("bus-density");
  badge.className = `badge ${densityClass(bus.density)}`;
  badge.textContent = densityLabel(bus.density);
}

async function sendReport(level) {
  const bus = state.bus;
  try {
    await api("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ route_id: bus.route_id, bus_id: bus.id, level }),
    });
    showToast("Təşəkkürlər, bildirişiniz qəbul edildi");
    hide("bus-panel");
    state.bus = null;
    refreshBuses();
    refreshEta();
  } catch (error) {
    showToast("Xəta baş verdi, yenidən cəhd edin");
  }
}

// --- Wiring ---

document.querySelectorAll(".report-buttons button").forEach((button) =>
  button.addEventListener("click", () => sendReport(button.dataset.level))
);

document.querySelectorAll("[data-close]").forEach((button) =>
  button.addEventListener("click", () => {
    hide(button.dataset.close);
    if (button.dataset.close === "eta-card") state.stop = null;
    if (button.dataset.close === "bus-panel") state.bus = null;
  })
);

loadRoutes();
setInterval(() => {
  refreshBuses().catch(console.error);
  refreshEta().catch(console.error);
}, POLL_MS);
