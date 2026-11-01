from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from lib import api, fmt

st.title("Trip reports")

drivers = api.safe(api.get, "/drivers") or []
today = datetime.now(fmt.DISPLAY_TZ).date()
c1, c2, c3 = st.columns(3)
start = c1.date_input("From", today - timedelta(days=30))
end = c2.date_input("To", today)
dlabel = {None: "All drivers"} | {d["id"]: d["name"] for d in drivers}
did = c3.selectbox("Driver", list(dlabel), format_func=dlabel.get)

rep = api.safe(api.get, "/reports/trips",
               start=datetime.combine(start, time.min, tzinfo=fmt.DISPLAY_TZ).isoformat(),
               end=datetime.combine(end, time.max, tzinfo=fmt.DISPLAY_TZ).isoformat(), driver_id=did)
if rep is None:
    st.stop()

s = rep["summary"]
by = s["by_status"]
active = sum(v for k, v in by.items() if k not in ("DELIVERED", "CANCELLED"))
delivered = [r for r in rep["trips"] if r["status"] == "DELIVERED"]
on_time = [r for r in delivered if r["on_time"] is not None]
m = st.columns(6)
m[0].metric("Trips", s["trips"])
m[1].metric("Active", active)
m[2].metric("Delivered", by.get("DELIVERED", 0))
m[3].metric("Cancelled", by.get("CANCELLED", 0))
m[4].metric("Distance (delivered)", f"{s['delivered_distance_km']} km")
m[5].metric("On-time", f"{100 * sum(r['on_time'] for r in on_time) / len(on_time):.0f}%" if on_time else "–")

if not rep["trips"]:
    st.info("No trips in this period.")
    st.stop()

df = pd.DataFrame([{
    "Trip": r["trip_id"], "Shipment": r["shipment_id"], "Status": fmt.status(r["status"]),
    "Driver": r["driver"] or "–", "Vehicle": r["vehicle"] or "–", "Started": fmt.local(r["started_at"]),
    "Ended": fmt.local(r["ended_at"]), "Distance (km)": r["distance_km"], "Planned (km)": r["planned_distance_km"],
    "Duration (min)": r["duration_min"],
    "On time": {True: "Yes", False: "No", None: "–"}[r["on_time"]],
} for r in rep["trips"]])
st.dataframe(df, hide_index=True, use_container_width=True)
st.download_button("Download CSV", df.to_csv(index=False), file_name=f"trip_report_{start}_{end}.csv",
                   mime="text/csv")
