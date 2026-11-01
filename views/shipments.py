import pandas as pd
import streamlit as st

from lib import api, fmt
from views import components

st.title("Shipments")

with st.expander("➕ New shipment", expanded=False):
    with st.form("new_shipment", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        customer = c1.text_input("Customer name *")
        phone = c2.text_input("Customer phone (WhatsApp/SMS)")
        email = c3.text_input("Customer email")
        c1, c2, c3 = st.columns(3)
        reference = c1.text_input("Reference / PO no.")
        description = c2.text_input("Goods description")
        weight = c3.number_input("Weight (kg)", min_value=0.0, step=100.0)

        st.markdown("**Pickup**")
        c1, c2, c3 = st.columns([3, 1, 1])
        p_addr = c1.text_input("Pickup address *")
        p_lat = c2.number_input("Latitude", value=13.0285, format="%.6f", key="plat")
        p_lon = c3.number_input("Longitude", value=77.5197, format="%.6f", key="plon")
        st.markdown("**Destination**")
        c1, c2, c3 = st.columns([3, 1, 1])
        d_addr = c1.text_input("Destination address *")
        d_lat = c2.number_input("Latitude", value=13.3409, format="%.6f", key="dlat")
        d_lon = c3.number_input("Longitude", value=77.1010, format="%.6f", key="dlon")
        require_otp = st.checkbox("Require delivery OTP from receiver", value=True)

        if st.form_submit_button("Create shipment", type="primary"):
            if not (customer and p_addr and d_addr):
                st.error("Customer, pickup address and destination address are required.")
            else:
                s = api.safe(api.post, "/shipments", {
                    "customer_name": customer, "customer_phone": phone or None, "customer_email": email or None,
                    "reference": reference or None, "description": description or None,
                    "weight_kg": weight or None, "pickup_address": p_addr, "pickup_lat": p_lat,
                    "pickup_lon": p_lon, "drop_address": d_addr, "drop_lat": d_lat, "drop_lon": d_lon,
                    "require_otp": require_otp,
                })
                if s:
                    st.success(f"Shipment {s['id']} created. Create a trip for it on the Trips page.")

shipments = api.safe(api.get, "/shipments") or []
if not shipments:
    st.info("No shipments yet.")
    st.stop()

df = pd.DataFrame([{
    "Shipment": s["id"], "Reference": s["reference"] or "", "Customer": s["customer_name"],
    "Status": fmt.status(s["status"]) if s["status"] != "BOOKED" else "Booked",
    "Pickup": s["pickup"]["address"], "Destination": s["drop"]["address"],
    "Weight (kg)": s["weight_kg"], "Created": fmt.local(s["created_at"]),
} for s in shipments])
sel = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
if sel.selection.rows:
    sid = df.iloc[sel.selection.rows[0]]["Shipment"]
    shp = api.safe(api.get, f"/shipments/{sid}")
    if shp:
        st.subheader(sid)
        st.markdown(f"**Customer** {shp['customer_name']} · {shp['customer_phone'] or '–'} · "
                    f"{shp['customer_email'] or '–'}  \n**Goods** {shp['description'] or '–'} "
                    f"({shp['weight_kg'] or '?'} kg)  \n**Delivery OTP** `{shp['delivery_otp']}`")
        st.markdown("**Trips** " + (", ".join(f"{t['id']} ({fmt.status(t['status'])})" for t in shp["trips"])
                                    or "none yet"))
        components.tracking_links(sid)
