import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from lib import api, fmt, maps

st.title("Live fleet map")
only_on_trip = st.toggle("Only trucks on a trip", value=False)


@st.fragment(run_every=10)
def live() -> None:
    fleet = api.safe(api.get, "/fleet/live")
    if fleet is None:
        return
    if only_on_trip:
        fleet = [f for f in fleet if f["trip"]]

    buckets = {"fresh": 0, "moderate": 0, "stale": 0, "none": 0}
    for f in fleet:
        loc = f["last_location"]
        f["_fresh"] = maps.freshness(loc["age_sec"] if loc else None)
        buckets[f["_fresh"]] += 1

    cols = st.columns(5)
    cols[0].metric("Trucks", len(fleet))
    for col, key in zip(cols[1:], ("fresh", "moderate", "stale", "none")):
        col.metric(maps.FRESHNESS_LABEL[key], buckets[key])

    located = [f for f in fleet if f["last_location"]]
    m = maps.base_map([(f["last_location"]["lat"], f["last_location"]["lon"]) for f in located])
    for f in located:
        loc = f["last_location"]
        reg = f["vehicle"]["reg_no"] if f["vehicle"] else "No vehicle"
        trip = f["trip"]
        maps.truck_marker(m, loc["lat"], loc["lon"], maps.FRESHNESS_COLOR[f["_fresh"]], f"{reg} · {f['driver']['name']}", {
            "Vehicle": reg, "Driver": f["driver"]["name"], "Phone": f["driver"]["phone"],
            "Trip": f"{trip['id']} ({fmt.status(trip['status'])})" if trip else "–",
            "Last update": f"{fmt.local(loc['ts'])} ({fmt.ago(loc['received_at'])})",
            "Speed": f"{loc['speed_kmph'] or 0} km/h", "Accuracy": f"±{loc['acc'] or '?'} m",
        })
    st_folium(m, height=560, use_container_width=True, returned_objects=[], key="live_map")

    rows = [{
        "Vehicle": f["vehicle"]["reg_no"] if f["vehicle"] else "–",
        "Driver": f["driver"]["name"],
        "Trip": f["trip"]["id"] if f["trip"] else "–",
        "Status": fmt.status(f["trip"]["status"]) if f["trip"] else "Idle",
        "Last update": fmt.local(f["last_location"]["ts"]) if f["last_location"] else "–",
        "Age": fmt.ago(f["last_location"]["received_at"]) if f["last_location"] else "never",
        "Speed (km/h)": f["last_location"]["speed_kmph"] if f["last_location"] else None,
    } for f in fleet]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(f"Auto-refreshes every 10 s · {fmt.local(pd.Timestamp.utcnow().isoformat(), with_date=False)}")


live()
