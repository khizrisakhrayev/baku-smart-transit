// Shared helpers for the passenger and operator pages (loaded before the page script).

const POLL_MS = 3000;
const BAKU_CENTER = [40.41, 49.87];
const DENSITY_LABELS = { low: "Aşağı", medium: "Orta", high: "Yüksək" };
const DENSITY_COLORS = { low: "#22a06b", medium: "#f59e0b", high: "#e5484d" };
const UNKNOWN_COLOR = "#8a94a6";
// The three accent colors (validated to stay distinguishable, incl. color blindness).
const ACCENT_COLORS = ["#2563eb", "#db2777", "#0891b2"];
const PRIMARY_COLOR = ACCENT_COLORS[0];
const TEXT_COLOR = "#1c2333";

// --- Data ---

// Throws on HTTP errors; error.detail holds the server's message (e.g. rate limit) if any.
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(`${response.status} ${path}`);
    error.detail = typeof body.detail === "string" ? body.detail : null;
    throw error;
  }
  return response.json();
}

// Search matches the route number, route name or any of its stop names.
function routeMatches(route, query) {
  const text = [route.id, route.name, ...route.stops.map((s) => s.name)].join(" ");
  return text.toLocaleLowerCase("az").includes(query.trim().toLocaleLowerCase("az"));
}

// --- Formatting ---

function densityClass(level) {
  return `density-${level || "unknown"}`;
}

function densityLabel(level) {
  return DENSITY_LABELS[level] || "Məlum deyil";
}

function densityColor(level) {
  return DENSITY_COLORS[level] || UNKNOWN_COLOR;
}

function badge(level) {
  return `<span class="badge ${densityClass(level)}">${densityLabel(level)}</span>`;
}

function formatTime(isoText) {
  if (!isoText) return "—";
  return new Date(isoText).toLocaleTimeString("az-AZ", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// --- Page UI ---

function show(id) { document.getElementById(id).hidden = false; }
function hide(id) { document.getElementById(id).hidden = true; }

function showToast(text) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("visible"), 3500);
}

// --- Map ---

function createMap(elementId) {
  const map = L.map(elementId, { zoomControl: false }).setView(BAKU_CENTER, 12);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  return map;
}

// Front view of a bus: body in the density color, outlined in `outline`
// (the route color on the passenger page, white on the operator page).
function busSvg(bodyColor, outline) {
  return `
    <svg viewBox="0 0 28 32" width="28" height="32" aria-hidden="true">
      <rect x="2" y="2" width="24" height="25" rx="5" fill="${bodyColor}" stroke="${outline}" stroke-width="2"/>
      <rect x="5.5" y="6" width="17" height="9" rx="2" fill="#fff" opacity="0.92"/>
      <circle cx="8" cy="21" r="2" fill="#fff"/>
      <circle cx="20" cy="21" r="2" fill="#fff"/>
      <rect x="5" y="27" width="5" height="4" rx="1.5" fill="${TEXT_COLOR}"/>
      <rect x="18" y="27" width="5" height="4" rx="1.5" fill="${TEXT_COLOR}"/>
    </svg>`;
}

function busIcon(bus, outline = "#fff") {
  return L.divIcon({
    className: "bus-icon",
    html: `
      <div class="bus-marker" style="--route-color: ${outline === "#fff" ? TEXT_COLOR : outline}">
        ${busSvg(densityColor(bus.density), outline)}
        <span class="bus-label">${bus.route_id}</span>
      </div>`,
    iconSize: [36, 48],
    iconAnchor: [18, 17], // centre of the bus body
  });
}

// Keeps `markers` (bus id -> Leaflet marker) in sync with `buses`: adds, moves and removes.
// options.outline(bus): icon outline color; options.onClick(bus); options.tooltip(bus).
function syncBusMarkers(map, markers, buses, options = {}) {
  const outline = options.outline || (() => "#fff");
  const seen = new Set();
  for (const bus of buses) {
    seen.add(bus.id);
    const iconKey = `${bus.density}|${outline(bus)}`;
    let marker = markers[bus.id];
    if (!marker) {
      marker = L.marker([bus.lat, bus.lon], { icon: busIcon(bus, outline(bus)), zIndexOffset: 1000 }).addTo(map);
      if (options.onClick) marker.on("click", () => options.onClick(marker.bus));
      if (options.tooltip) marker.bindTooltip(() => options.tooltip(marker.bus));
      markers[bus.id] = marker;
    } else if (marker.iconKey !== iconKey) {
      marker.setIcon(busIcon(bus, outline(bus))); // only when needed, so the glide animation survives
    }
    marker.iconKey = iconKey;
    marker.bus = bus;
    marker.setLatLng([bus.lat, bus.lon]);
  }
  for (const [id, marker] of Object.entries(markers)) {
    if (!seen.has(id)) {
      marker.remove();
      delete markers[id];
    }
  }
}

// --- Live updates: Server-Sent Events, with polling as the automatic fallback ---

const live = { connected: false };

function setLive(connected) {
  live.connected = connected;
  const indicator = document.getElementById("live-indicator");
  indicator.textContent = connected ? "Canlı" : "Polling";
  indicator.classList.toggle("live", connected);
}

// While the stream is open, data arrives by push; on any error we drop back to polling
// (EventSource keeps retrying by itself and we switch back when it reconnects).
function startLiveStream(handlers) {
  if (!window.EventSource) return;
  const source = new EventSource("/api/stream");
  source.addEventListener("open", () => setLive(true));
  source.addEventListener("error", () => setLive(false));
  for (const [event, handle] of Object.entries(handlers)) {
    source.addEventListener(event, (message) => handle(JSON.parse(message.data)));
  }
}
