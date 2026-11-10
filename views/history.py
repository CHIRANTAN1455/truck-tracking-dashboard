"""Location history with playback (port of tracking-dashboard's VehicleTrail + PlaybackControls)."""

from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from lib import api, fmt, maps

st.title("Location history")

mode = st.radio("Show history for", ["Trip", "Driver"], horizontal=True)
trip = None

if mode == "Trip":
    trips = api.safe(api.get, "/trips") or []
    trips = [t for t in trips if t["started_at"]]
    if not trips:
        st.info("No trips have started yet.")
        st.stop()
    label = {t["id"]: f"{t['id']} · {fmt.status(t['status'])} · {t['vehicle']['reg_no'] if t['vehicle'] else ''} · "
                      f"{fmt.local(t['started_at'])}" for t in trips}
    tid = st.selectbox("Trip", list(label), format_func=label.get)
    trip = api.safe(api.get, f"/trips/{tid}")
    points = api.safe(api.get, f"/trips/{tid}/locations") or []
else:
    drivers = api.safe(api.get, "/drivers") or []
    if not drivers:
        st.info("No drivers.")
        st.stop()
    dmap = {d["id"]: d for d in drivers}
    c1, c2, c3 = st.columns([2, 1, 1])
    did = c1.selectbox("Driver", list(dmap), format_func=lambda x: f"{dmap[x]['name']} · "
                       f"{dmap[x]['company']['code'] if dmap[x]['company'] else '–'} · {dmap[x]['phone']}")
    today = datetime.now(fmt.DISPLAY_TZ).date()
    start = c2.date_input("From", today - timedelta(days=1))
    end = c3.date_input("To", today)
    points = api.safe(api.get, f"/drivers/{did}/locations",
                      start=datetime.combine(start, time.min, tzinfo=fmt.DISPLAY_TZ).isoformat(),
                      end=datetime.combine(end, time.max, tzinfo=fmt.DISPLAY_TZ).isoformat()) or []

if not points:
    st.info("No location points recorded for this selection.")
    st.stop()

upto = st.slider("Playback", min_value=1, max_value=len(points), value=len(points),
                 help="Drag to replay the route point by point")
cur = points[upto - 1]
c = st.columns(4)
c[0].metric("Point", f"{upto} / {len(points)}")
c[1].metric("Time", fmt.local(cur["ts"]))
c[2].metric("Speed", f"{cur['speed_kmph'] or 0} km/h")
c[3].metric("Source", fmt.source(cur.get("source"), cur.get("acc")))

if trip:
    m = maps.trip_map(trip, points, upto=upto)
else:
    shown = points[:upto]
    m = maps.base_map([(p["lat"], p["lon"]) for p in shown])
    maps.route_line(m, [(p["lat"], p["lon"]) for p in shown])
    if cur.get("source") == "sim":
        maps.accuracy_circle(m, cur["lat"], cur["lon"], cur["acc"])
    maps.truck_marker(m, cur["lat"], cur["lon"], "blue", fmt.local(cur["ts"]), {"Time": fmt.local(cur["ts"])})
st_folium(m, height=500, use_container_width=True, returned_objects=[], key="history_map")

df = pd.DataFrame([{"Time": fmt.local(p["ts"]), "Lat": p["lat"], "Lon": p["lon"], "Speed (km/h)": p["speed_kmph"],
                    "Accuracy (m)": p["acc"], "Source": p.get("source") or "", "Used for distance": p["accurate"],
                    "Trip": p["trip_id"] or ""}
                   for p in points])
st.dataframe(df, hide_index=True, use_container_width=True, height=260)
st.download_button("Download CSV", df.to_csv(index=False), file_name="location_history.csv", mime="text/csv")
