// Passenger view: up to 3 routes on the map, live buses, stop ETAs and density reporting.

const MAX_ROUTES = 3;
const STOP_ZOOM = 14; // stop dots appear from this zoom (the selected stop always shows)

const state = {
  routes: {},         // route id -> route (with stops)
  selected: [],       // selected route ids, in the order they were added
  colors: {},         // route id -> line color; kept while selected, so colors never shuffle
  lines: {},          // route id -> Leaflet polyline
  stop: null,         // stop whose ETAs are shown
  bus: null,          // bus whose report panel is open
  busMarkers: {},     // bus id -> Leaflet marker
};

const map = createMap("map");
const stopLayer = L.layerGroup().addTo(map);
map.on("zoomend", drawStops);

// --- Route selection (chips) ---

async function loadRoutes() {
  const routes = await api("/api/routes");
  routes.forEach((route) => (state.routes[route.id] = route));
  document.getElementById("route-search").addEventListener("input", fillRouteSelect);
  document.getElementById("route-select").addEventListener("change", (event) => {
    if (event.target.value) addRoute(event.target.value);
  });
  fillRouteSelect();
  addRoute(routes[0].id);
}

function fillRouteSelect() {
  const query = document.getElementById("route-search").value;
  const matches = Object.values(state.routes)
    .filter((route) => !state.selected.includes(route.id) && routeMatches(route, query));
  const select = document.getElementById("route-select");
  select.innerHTML = "";
  select.add(new Option(matches.length ? "+ Marşrut əlavə et" : "Heç nə tapılmadı", ""));
  for (const route of matches) select.add(new Option(`${route.id} · ${route.name}`, route.id));
}

function addRoute(routeId) {
  if (state.selected.length >= MAX_ROUTES) {
    showToast(`Ən çox ${MAX_ROUTES} marşrut seçmək olar`);
    fillRouteSelect();
    return;
  }
  const usedColors = Object.values(state.colors);
  state.colors[routeId] = ACCENT_COLORS.find((color) => !usedColors.includes(color));
  state.selected.push(routeId);
  const route = state.routes[routeId];
  state.lines[routeId] = L.polyline(route.stops.map((s) => [s.lat, s.lon]),
    { color: state.colors[routeId], weight: 5, opacity: 0.8 }).addTo(map);
  onRoutesChanged();
  map.fitBounds(state.lines[routeId].getBounds(), { padding: [40, 40] });
}

function removeRoute(routeId) {
  state.selected = state.selected.filter((id) => id !== routeId);
  delete state.colors[routeId];
  state.lines[routeId].remove();
  delete state.lines[routeId];
  if (state.stop && !selectedRoutesWithStop(state.stop.id).length) closeEta();
  onRoutesChanged();
}

function onRoutesChanged() {
  document.getElementById("route-search").value = "";
  fillRouteSelect();
  renderChips();
  renderStopList();
  drawStops();
  refreshBuses().catch(console.error);
}

function renderChips() {
  const chips = document.getElementById("route-chips");
  if (!state.selected.length) {
    chips.innerHTML = '<li class="empty">Xəritədə görmək üçün yuxarıdan marşrut seçin.</li>';
    return;
  }
  chips.innerHTML = state.selected.map((id) => `
    <li class="chip" style="--route-color: ${state.colors[id]}">
      <span class="chip-swatch"></span>
      <strong>${id}</strong>
      <span class="chip-name">${state.routes[id].name}</span>
      <button class="chip-remove" data-remove-route="${id}" aria-label="Sil: Marşrut ${id}">×</button>
    </li>`).join("");
}

// --- Stops ---

function selectedRoutesWithStop(stopId) {
  return state.selected.filter((id) => state.routes[id].stops.some((s) => s.id === stopId));
}

// Stop dots only when zoomed in (the map stays clean), but the selected stop always shows.
function drawStops() {
  stopLayer.clearLayers();
  const showAll = map.getZoom() >= STOP_ZOOM;
  const drawn = new Set();
  for (const routeId of state.selected) {
    for (const stop of state.routes[routeId].stops) {
      const isSelected = state.stop && state.stop.id === stop.id;
      if (drawn.has(stop.id) || !(showAll || isSelected)) continue;
      drawn.add(stop.id);
      L.circleMarker([stop.lat, stop.lon], {
        radius: isSelected ? 9 : 6,
        color: state.colors[routeId],
        weight: 3,
        fillColor: isSelected ? state.colors[routeId] : "#fff",
        fillOpacity: 1,
      }).bindTooltip(stop.name).on("click", () => showStop(stop)).addTo(stopLayer);
    }
  }
}

function renderStopList() {
  const container = document.getElementById("stop-list");
  if (!state.selected.length) {
    container.innerHTML = '<p class="empty">Marşrut seçildikdə dayanacaqlar burada görünəcək.</p>';
    return;
  }
  container.innerHTML = state.selected.map((id) => `
    <h3 class="stop-group" style="--route-color: ${state.colors[id]}">
      <span class="chip-swatch"></span>Marşrut ${id}
    </h3>
    <ol class="stop-list">
      ${state.routes[id].stops.map((stop) => `
        <li data-stop-id="${stop.id}" class="${state.stop && state.stop.id === stop.id ? "active" : ""}">
          ${stop.name}
        </li>`).join("")}
    </ol>`).join("");
}

// --- Stop ETAs ---

function showStop(stop) {
  state.stop = stop;
  document.getElementById("eta-title").textContent = stop.name;
  show("eta-card");
  renderStopList();
  drawStops();
  refreshEta().catch(console.error);
}

function closeEta() {
  state.stop = null;
  hide("eta-card");
  renderStopList();
  drawStops();
}

function routeTag(routeId) {
  const color = state.colors[routeId] || TEXT_COLOR; // routes not on the map: neutral
  return `<span class="route-tag" style="--route-color: ${color}">${routeId}</span>`;
}

function formatMinutes(minutes) {
  if (minutes < 1) return "1 dəq-dən az";
  return `${Math.round(minutes)} dəq`;
}

async function refreshEta() {
  if (!state.stop) return;
  const etas = await api(`/api/stops/${state.stop.id}/eta`);
  const list = document.getElementById("eta-list");
  if (!etas.length) {
    list.innerHTML = '<li class="empty">Bu dayanacağa yaxınlaşan avtobus yoxdur.</li>';
    return;
  }
  list.innerHTML = etas.map((eta) => `
    <li class="${eta.most_comfortable ? "comfortable" : ""}">
      ${routeTag(eta.route_id)}
      <span class="eta-bus">
        Avtobus ${eta.bus_id}
        ${eta.most_comfortable ? '<span class="comfort-badge">⭐ Ən rahat seçim</span>' : ""}
      </span>
      ${badge(eta.density)}
      <strong class="eta-time">${formatMinutes(eta.eta_minutes)}</strong>
      ${suggestionBox(eta.suggestion)}
    </li>`).join("");
}

// Hint under a crowded bus: a less crowded bus worth waiting for (from the server).
function suggestionBox(suggestion) {
  if (!suggestion) return "";
  const minutes = Math.max(1, Math.round(suggestion.eta_minutes));
  return `
    <div class="suggestion">
      💡 Bu avtobus doludur. Marşrut ${suggestion.route_id} ${minutes} dəq sonra gəlir
      (sıxlıq: ${densityLabel(suggestion.density)})
    </div>`;
}

// --- Live buses (selected routes only) ---

async function refreshBuses() {
  renderBuses(await api("/api/buses"));
}

function renderBuses(allBuses) {
  const buses = allBuses.filter((bus) => state.selected.includes(bus.route_id));
  syncBusMarkers(map, state.busMarkers, buses, {
    outline: (bus) => state.colors[bus.route_id],
    onClick: openBusPanel,
  });
  const open = state.bus && buses.find((bus) => bus.id === state.bus.id);
  if (open) renderBusPanel(open);
}

// --- Density reporting ---

// Anonymous id kept in this browser, so the server can rate-limit and count unique reporters.
function getClientId() {
  let id = localStorage.getItem("clientId");
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now();
    localStorage.setItem("clientId", id);
  }
  return id;
}

// Current position if the passenger allows it, otherwise null (the report is sent without it).
function getPosition() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => resolve(null),
      { timeout: 5000, maximumAge: 60000 }
    );
  });
}

function openBusPanel(bus) {
  renderBusPanel(bus);
  show("bus-panel");
}

function renderBusPanel(bus) {
  state.bus = bus;
  document.getElementById("bus-title").textContent = `Avtobus ${bus.id} · Marşrut ${bus.route_id}`;
  const densityBadge = document.getElementById("bus-density");
  densityBadge.className = `badge ${densityClass(bus.density)}`;
  densityBadge.textContent = densityLabel(bus.density);
}

async function sendReport(level) {
  const bus = state.bus;
  const buttons = document.querySelectorAll(".report-buttons button");
  buttons.forEach((b) => (b.disabled = true)); // geolocation can take a few seconds
  try {
    const position = await getPosition();
    await api("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ route_id: bus.route_id, bus_id: bus.id, level, client_id: getClientId(), ...position }),
    });
    showToast("Təşəkkürlər, bildirişiniz qəbul edildi");
    hide("bus-panel");
    state.bus = null;
    refreshBuses().catch(console.error);
    refreshEta().catch(console.error);
  } catch (error) {
    showToast(error.detail || "Xəta baş verdi, yenidən cəhd edin");
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}

// --- Wiring (lists are re-rendered, so listen on their containers) ---

document.getElementById("route-chips").addEventListener("click", (event) => {
  const routeId = event.target.dataset.removeRoute;
  if (routeId) removeRoute(routeId);
});

document.getElementById("stop-list").addEventListener("click", (event) => {
  const item = event.target.closest("[data-stop-id]");
  if (!item) return;
  const stop = state.selected.flatMap((id) => state.routes[id].stops).find((s) => s.id === item.dataset.stopId);
  map.panTo([stop.lat, stop.lon]);
  showStop(stop);
});

document.querySelectorAll(".report-buttons button").forEach((button) =>
  button.addEventListener("click", () => sendReport(button.dataset.level))
);

document.querySelector('[data-close="eta-card"]').addEventListener("click", closeEta);
document.querySelector('[data-close="bus-panel"]').addEventListener("click", () => {
  hide("bus-panel");
  state.bus = null;
});

loadRoutes().catch(console.error);
startLiveStream({ buses: renderBuses });
setInterval(() => {
  if (!live.connected) refreshBuses().catch(console.error);
  refreshEta().catch(console.error);
}, POLL_MS);
