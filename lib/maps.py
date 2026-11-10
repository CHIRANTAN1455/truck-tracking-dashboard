"""Folium map helpers. Marker colours follow nammayatri/tracking-dashboard (green / orange / red / grey),
but freshness is judged against how often a truck is expected to report: app GPS every ~30 s, SIM
(network) tracking every SIM_PING_ON_TRIP_MIN. SIM fixes are drawn with their accuracy circle."""

import html

import folium

from . import fmt

DEFAULT_CENTER = (12.9716, 77.5946)  # Bengaluru

FRESH_SEC, MODERATE_SEC = 60, 300


def freshness(age_sec: int | None, interval_sec: int | None = None) -> str:
    """fresh = within the expected update interval, moderate = missed about one update, stale = more."""
    if age_sec is None:
        return "none"
    fresh, moderate = (FRESH_SEC, MODERATE_SEC) if not interval_sec or interval_sec <= 60 \
        else (interval_sec * 1.2, interval_sec * 2.5)
    if age_sec < fresh:
        return "fresh"
    if age_sec < moderate:
        return "moderate"
    return "stale"


FRESHNESS_COLOR = {"fresh": "green", "moderate": "orange", "stale": "red", "none": "gray"}
FRESHNESS_LABEL = {"fresh": "On schedule", "moderate": "1 update missed", "stale": "Stale", "none": "No location"}
COMPANY_COLORS = ["#0f766e", "#7c3aed", "#c2410c", "#1d4ed8", "#be185d", "#4d7c0f"]


def company_color(company_id: int | None) -> str:
    return "#64748b" if company_id is None else COMPANY_COLORS[(company_id - 1) % len(COMPANY_COLORS)]


def accuracy_circle(m, lat: float, lon: float, acc_m: float | None, color: str = "#2563eb") -> None:
    """Area the truck is in, for network (SIM) fixes."""
    if acc_m:
        folium.Circle((lat, lon), radius=acc_m, color=color, weight=1, fill=True, fill_opacity=0.08,
                      opacity=0.5).add_to(m)


def base_map(points: list[tuple[float, float]] | None = None, zoom: int = 11) -> folium.Map:
    m = folium.Map(location=points[0] if points else DEFAULT_CENTER, zoom_start=zoom, tiles="OpenStreetMap",
                   control_scale=True)
    if points and len(points) > 1:
        lats, lons = [p[0] for p in points], [p[1] for p in points]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    return m


def truck_marker(m, lat: float, lon: float, color: str, tooltip: str, popup_rows: dict) -> None:
    rows = "".join(f"<tr><td style='color:#666;padding-right:8px'>{html.escape(str(k))}</td>"
                   f"<td><b>{html.escape(str(v))}</b></td></tr>" for k, v in popup_rows.items())
    folium.Marker(
        (lat, lon), tooltip=html.escape(tooltip),
        popup=folium.Popup(f"<table style='font-size:13px'>{rows}</table>", max_width=320),
        icon=folium.Icon(color=color, icon="truck", prefix="fa"),
    ).add_to(m)


def place_marker(m: folium.Map, lat: float, lon: float, kind: str, label: str) -> None:
    icon = folium.Icon(color="blue", icon="warehouse", prefix="fa") if kind == "pickup" \
        else folium.Icon(color="darkred", icon="flag-checkered", prefix="fa")
    folium.Marker((lat, lon), tooltip=f"{'Pickup' if kind == 'pickup' else 'Destination'}: {html.escape(label)}",
                  icon=icon).add_to(m)


def route_line(m: folium.Map, coords: list, planned: bool = False) -> None:
    if len(coords) < 2:
        return
    if planned:
        folium.PolyLine(coords, color="#64748b", weight=3, dash_array="8 8", tooltip="Planned route").add_to(m)
    else:
        folium.PolyLine(coords, color="#0f766e", weight=4, opacity=0.9, tooltip="Travelled path").add_to(m)


def trip_map(trip: dict, trail: list[dict], upto: int | None = None) -> folium.Map:
    """Planned route, travelled trail (optionally only the first `upto` points), pickup, drop, truck."""
    s = trip["shipment"]
    pick, drop = (s["pickup"]["lat"], s["pickup"]["lon"]), (s["drop"]["lat"], s["drop"]["lon"])
    shown = trail if upto is None else trail[:upto]
    pts = [pick, drop] + [(p["lat"], p["lon"]) for p in shown]
    m = base_map(pts)
    route_line(m, trip.get("planned_route") or [list(pick), list(drop)], planned=True)
    route_line(m, [(p["lat"], p["lon"]) for p in shown])
    place_marker(m, *pick, "pickup", s["pickup"]["address"])
    place_marker(m, *drop, "drop", s["drop"]["address"])
    current = shown[-1] if shown else None
    if upto is None and trip.get("last_location"):
        current = trip["last_location"]
    if current:
        age = current.get("age_sec")
        sim = current.get("source") == "sim"
        color = FRESHNESS_COLOR[freshness(age, 600 if sim else None)] if upto is None else "blue"
        if sim:
            accuracy_circle(m, current["lat"], current["lon"], current.get("acc"))
        truck_marker(m, current["lat"], current["lon"], color, trip["vehicle"]["reg_no"] if trip.get("vehicle")
                     else "Truck", {"Time": fmt.local(current["ts"]), "Speed": f"{current.get('speed_kmph') or 0} km/h",
                      "Source": fmt.source(current.get("source"), current.get("acc"))})
    return m
