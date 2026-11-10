import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from lib import api, fmt, maps

st.title("Live fleet map")

companies = api.safe(api.get, "/companies") or []
cmap = {c["id"]: c for c in companies}
c1, c2, c3 = st.columns([3, 1, 1])
picked = c1.multiselect("Companies", list(cmap), format_func=lambda x: cmap[x]["name"],
                        placeholder="All companies")
only_on_trip = c2.toggle("Only trucks on a trip", value=False)
show_circles = c3.toggle("Show SIM accuracy", value=True,
                         help="SIM (network) fixes are approximate; the circle is the area the truck is in.")


@st.fragment(run_every=15)
def live() -> None:
    fleet = api.safe(api.get, "/fleet/live")
    if fleet is None:
        return
    if picked:
        fleet = [f for f in fleet if f["company"] and f["company"]["id"] in picked]
    if only_on_trip:
        fleet = [f for f in fleet if f["trip"]]

    buckets = {"fresh": 0, "moderate": 0, "stale": 0, "none": 0}
    for f in fleet:
        loc = f["last_location"]
        f["_fresh"] = maps.freshness(loc["age_sec"] if loc else None, f.get("expected_interval_sec"))
        buckets[f["_fresh"]] += 1

    cols = st.columns(6)
    cols[0].metric("Trucks", len(fleet))
    cols[1].metric("On a trip", sum(1 for f in fleet if f["trip"]))
    for col, key in zip(cols[2:], ("fresh", "moderate", "stale", "none")):
        col.metric(maps.FRESHNESS_LABEL[key], buckets[key])

    located = [f for f in fleet if f["last_location"]]
    m = maps.base_map([(f["last_location"]["lat"], f["last_location"]["lon"]) for f in located], zoom=5)
    # One toggleable layer per company (top-right layer control on the map).
    layers: dict = {}
    for f in located:
        comp = f["company"]
        key = comp["id"] if comp else None
        if key not in layers:
            layers[key] = folium.FeatureGroup(name=comp["name"] if comp else "No company").add_to(m)
        layer = layers[key]
        loc = f["last_location"]
        reg = f["vehicle"]["reg_no"] if f["vehicle"] else "No vehicle"
        trip = f["trip"]
        if show_circles and loc.get("source") == "sim":
            maps.accuracy_circle(layer, loc["lat"], loc["lon"], loc["acc"], maps.company_color(key))
        maps.truck_marker(layer, loc["lat"], loc["lon"], maps.FRESHNESS_COLOR[f["_fresh"]],
                          f"{reg} · {f['driver']['name']} · {comp['code'] if comp else ''}", {
                              "Company": comp["name"] if comp else "–",
                              "Vehicle": reg, "Driver": f["driver"]["name"], "Phone": f["driver"]["phone"],
                              "Trip": f"{trip['id']} ({fmt.status(trip['status'])})" if trip else "–",
                              "Last update": f"{fmt.local(loc['ts'])} ({fmt.ago(loc['received_at'])})",
                              "Source": fmt.source(loc.get("source"), loc.get("acc")),
                              "SIM": fmt.sim_status(f["sim"]["status"] if f["sim"] else None),
                              "Speed": f"{loc['speed_kmph'] or 0} km/h",
                          })
    if len(layers) > 1:
        folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=600, use_container_width=True, returned_objects=[], key="live_map")

    if companies and not picked:
        st.markdown("#### By company")
        per = {}
        for f in fleet:
            name = f["company"]["name"] if f["company"] else "No company"
            row = per.setdefault(name, {"Company": name, "Trucks": 0, "On trip": 0, "On schedule": 0,
                                        "Stale / no location": 0, "SIM consent pending": 0})
            row["Trucks"] += 1
            row["On trip"] += bool(f["trip"])
            row["On schedule"] += f["_fresh"] == "fresh"
            row["Stale / no location"] += f["_fresh"] in ("stale", "none")
            row["SIM consent pending"] += bool(f["sim"]) and f["sim"]["status"] == "PENDING"
        st.dataframe(pd.DataFrame(sorted(per.values(), key=lambda r: -r["Trucks"])), hide_index=True,
                     use_container_width=True)

    rows = [{
        "Company": f["company"]["code"] if f["company"] else "–",
        "Vehicle": f["vehicle"]["reg_no"] if f["vehicle"] else "–",
        "Driver": f["driver"]["name"],
        "Trip": f["trip"]["id"] if f["trip"] else "–",
        "Status": fmt.status(f["trip"]["status"]) if f["trip"] else "Idle",
        "SIM": fmt.sim_status(f["sim"]["status"] if f["sim"] else None),
        "Last update": fmt.local(f["last_location"]["ts"]) if f["last_location"] else "–",
        "Age": fmt.ago(f["last_location"]["received_at"]) if f["last_location"] else "never",
        "Accuracy": fmt.distance(f["last_location"]["acc"]) if f["last_location"] else "–",
        "Speed (km/h)": f["last_location"]["speed_kmph"] if f["last_location"] else None,
    } for f in fleet]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(f"Auto-refreshes every 15 s · SIM trucks report every few minutes, so 'On schedule' is judged "
               f"against each truck's ping interval · {fmt.local(pd.Timestamp.utcnow().isoformat(), with_date=False)}")


live()
