from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from lib import api, fmt, maps
from views import components

st.title("Trips")

_companies = api.safe(api.get, "/companies") or []
_cmap = {c["id"]: c for c in _companies}
company_id = st.selectbox("Company", [None] + list(_cmap),
                          format_func=lambda x: "All companies" if x is None else _cmap[x]["name"])

tab_active, tab_done, tab_cancel, tab_new = st.tabs(["Active", "Completed", "Cancelled", "➕ Create trip"])


def trip_table(group: str, key: str) -> str | None:
    trips = api.safe(api.get, "/trips", group=group, company_id=company_id) or []
    if not trips:
        st.info("No trips.")
        return None
    df = pd.DataFrame([{
        "Trip": t["id"], "Status": fmt.status(t["status"]),
        "Company": t["company"]["code"] if t.get("company") else "–", "Shipment": t["shipment"]["id"],
        "Customer": t["shipment"]["customer_name"], "Driver": t["driver"]["name"] if t["driver"] else "–",
        "Vehicle": t["vehicle"]["reg_no"] if t["vehicle"] else "–",
        "From": t["shipment"]["pickup"]["address"], "To": t["shipment"]["drop"]["address"],
        "Km": t["distance_km"], "ETA": fmt.local(t["eta"]["eta"]) if t["eta"] else "–",
        "Expected by": fmt.local(t["expected_delivery_at"]),
        "Last update": fmt.ago(t["last_location"]["received_at"]) if t["last_location"] else "–",
        "Alerts": t["open_alerts"],
    } for t in trips])
    sel = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun",
                       selection_mode="single-row", key=f"tbl_{key}")
    rows = sel.selection.rows
    return df.iloc[rows[0]]["Trip"] if rows else None


def trip_detail(trip_id: str) -> None:
    t = api.safe(api.get, f"/trips/{trip_id}")
    if t is None:
        return
    s = t["shipment"]
    st.subheader(f"{t['id']} · {fmt.status(t['status'])}")

    c = st.columns(5)
    c[0].metric("Distance travelled", f"{t['distance_km']} km", help=f"Planned {t['planned_distance_km']} km")
    c[1].metric("Duration", f"{t['duration_min'] or 0:.0f} min")
    c[2].metric("ETA", fmt.local(t["eta"]["eta"]) if t["eta"] else "–",
                help=f"{t['eta']['remaining_km']} km left" if t["eta"] else None)
    c[3].metric("Last location update", fmt.ago(t["last_location"]["received_at"]) if t["last_location"] else "–")
    c[4].metric("Open alerts", t["open_alerts"])

    left, right = st.columns([3, 2])
    with left:
        trail = api.safe(api.get, f"/trips/{trip_id}/locations") or []
        st_folium(maps.trip_map(t, trail), height=430, use_container_width=True, returned_objects=[],
                  key=f"map_{trip_id}")
    with right:
        st.markdown(f"**Shipment** {s['id']} {('· ' + s['reference']) if s['reference'] else ''}")
        st.markdown(f"**Customer** {s['customer_name']} · {s['customer_phone'] or '–'} · {s['customer_email'] or '–'}")
        st.markdown(f"**Pickup** {s['pickup']['address']}")
        st.markdown(f"**Destination** {s['drop']['address']}")
        st.markdown(f"**Company** {t['company']['name'] if t.get('company') else '–'}")
        st.markdown(f"**Driver** {t['driver']['name'] + ' · ' + t['driver']['phone'] if t['driver'] else '–'}")
        if t["last_location"]:
            st.markdown(f"**Tracking** {fmt.source(t['last_location'].get('source'), t['last_location'].get('acc'))}")
        st.markdown(f"**Vehicle** {t['vehicle']['reg_no'] if t['vehicle'] else '–'}")
        st.markdown(f"**Expected by** {fmt.local(t['expected_delivery_at'])}")
        st.markdown(f"**Delivery OTP** `{s['delivery_otp']}` {'(required)' if s['require_otp'] else '(optional)'}")
        if t["route_source"] != "osrm":
            st.caption("Planned route is a straight line (no OSRM_URL configured on the backend).")

    st.markdown("#### Timeline")
    st.dataframe(pd.DataFrame([{"Status": fmt.status(e["status"]), "Time": fmt.local(e["ts"]), "Note": e["note"] or ""}
                               for e in t["events"]]), hide_index=True, use_container_width=True)

    actions(t)

    if t["pod"]:
        st.markdown("#### Proof of delivery")
        p = t["pod"]
        cols = st.columns([2, 1])
        cols[0].markdown(f"Received by **{p['receiver_name']}** {p['receiver_phone'] or ''}  \n"
                         f"Delivered {fmt.local(p['delivered_at'])} · OTP verified: "
                         f"{'✅' if p['otp_verified'] else '—'}  \n{p['notes'] or ''}")
        if p["has_photo"]:
            photo = api.safe(api.get, f"/trips/{trip_id}/pod/photo")
            if photo:
                try:
                    cols[1].image(photo, caption="POD photo", use_container_width=True)
                except Exception:
                    cols[1].download_button("Download POD photo", photo, file_name=f"pod_{trip_id}.jpg")

    components.tracking_links(s["id"])

    if t["alerts"]:
        st.markdown("#### Alerts")
        st.dataframe(pd.DataFrame([{"Type": fmt.ALERT_LABELS.get(a["kind"], a["kind"]), "Message": a["message"],
                                    "Raised": fmt.local(a["created_at"]),
                                    "Resolved": fmt.local(a["resolved_at"]) if a["resolved_at"] else "Open"}
                                   for a in t["alerts"]]), hide_index=True, use_container_width=True)


def actions(t: dict) -> None:
    status, tid = t["status"], t["id"]
    if status in ("DELIVERED", "CANCELLED"):
        return
    st.markdown("#### Actions")

    if status in ("CREATED", "ASSIGNED"):
        drivers = [d for d in (api.safe(api.get, "/drivers", company_id=company_id) or []) if d["active"]]
        if drivers:
            with st.form(f"assign_{tid}"):
                label = {d["id"]: f"{d['name']} · {d['company']['code'] if d['company'] else '–'} "
                                  f"({d['vehicle']['reg_no'] if d['vehicle'] else 'no vehicle'}) · "
                                  f"{fmt.sim_status(d['sim']['status'] if d['sim'] else None)}"
                         for d in drivers}
                did = st.selectbox("Driver", list(label), format_func=label.get)
                vehicles = [v for v in (api.safe(api.get, "/vehicles") or []) if v["active"]]
                vopts = [None] + [v["id"] for v in vehicles]
                vlabel = {v["id"]: v["reg_no"] for v in vehicles}
                vid = st.selectbox("Vehicle (default: driver's vehicle)", vopts,
                                   format_func=lambda x: "Driver's vehicle" if x is None else vlabel[x])
                if st.form_submit_button("Assign"):
                    if api.safe(api.post, f"/trips/{tid}/assign", {"driver_id": did, "vehicle_id": vid}):
                        st.rerun()

    nxt = {"ASSIGNED": ["PICKED_UP", "STARTED"], "PICKED_UP": ["STARTED"],
           "STARTED": ["IN_TRANSIT", "REACHED"], "IN_TRANSIT": ["REACHED"]}.get(status, [])
    cols = st.columns(max(len(nxt), 1) + 1)
    for i, ns in enumerate(nxt):
        if cols[i].button(f"Mark {fmt.status(ns).lower()}", key=f"st_{tid}_{ns}"):
            if api.safe(api.post, f"/trips/{tid}/status", {"status": ns}):
                st.rerun()

    with st.expander("Cancel trip"):
        reason = st.text_input("Reason", key=f"cr_{tid}")
        if st.button("Cancel trip", type="secondary", key=f"cancel_{tid}"):
            if api.safe(api.post, f"/trips/{tid}/cancel", {"reason": reason or "Cancelled by operator"}):
                st.rerun()

    if status in ("STARTED", "IN_TRANSIT", "REACHED"):
        with st.expander("Record proof of delivery"):
            with st.form(f"pod_{tid}"):
                name = st.text_input("Receiver name")
                phone = st.text_input("Receiver phone")
                otp = st.text_input("Delivery OTP (from customer)")
                notes = st.text_input("Notes")
                photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "webp"])
                if st.form_submit_button("Mark delivered", type="primary"):
                    if not name:
                        st.error("Receiver name is required")
                    else:
                        data = {"receiver_name": name, "receiver_phone": phone or None, "otp": otp or None,
                                "notes": notes or None}
                        files = {"photo": (photo.name, photo.getvalue(), photo.type)} if photo else None
                        if api.safe(api.request, "POST", f"/trips/{tid}/pod",
                                    data={k: v for k, v in data.items() if v}, files=files):
                            st.rerun()


def create_trip() -> None:
    shipments = [s for s in (api.safe(api.get, "/shipments") or []) if s["status"] in ("BOOKED", "CANCELLED")]
    if not shipments:
        st.info("No unassigned shipments. Create one on the Shipments page first.")
        return
    drivers = [d for d in (api.safe(api.get, "/drivers", company_id=company_id) or []) if d["active"]]
    with st.form("new_trip"):
        slabel = {s["id"]: f"{s['id']} · {s['customer_name']} · {s['pickup']['address']} → {s['drop']['address']}"
                  for s in shipments}
        sid = st.selectbox("Shipment", list(slabel), format_func=slabel.get)
        dlabel = {None: "Assign later"} | {
            d["id"]: f"{d['name']} · {d['company']['code'] if d['company'] else '–'} "
                     f"({d['vehicle']['reg_no'] if d['vehicle'] else 'no vehicle'}) · "
                     f"{fmt.sim_status(d['sim']['status'] if d['sim'] else None)}"
            for d in drivers}
        did = st.selectbox("Driver", list(dlabel), format_func=dlabel.get)
        c1, c2 = st.columns(2)
        set_eta = c1.checkbox("Set expected delivery time", value=True)
        day = c1.date_input("Expected delivery date", value=datetime.now(fmt.DISPLAY_TZ).date() + timedelta(days=1))
        tm = c2.time_input("Expected delivery time", value=time(18, 0))
        if st.form_submit_button("Create trip", type="primary"):
            body = {"shipment_id": sid, "driver_id": did}
            if set_eta:
                body["expected_delivery_at"] = datetime.combine(day, tm, tzinfo=fmt.DISPLAY_TZ).isoformat()
            t = api.safe(api.post, "/trips", body)
            if t:
                st.success(f"Trip {t['id']} created ({fmt.status(t['status'])}).")


for tab, group in ((tab_active, "active"), (tab_done, "completed"), (tab_cancel, "cancelled")):
    with tab:
        selected = trip_table(group, group)
        if selected:
            st.divider()
            trip_detail(selected)
        else:
            st.caption("Select a row to see the trip details, map and actions.")
with tab_new:
    create_trip()
