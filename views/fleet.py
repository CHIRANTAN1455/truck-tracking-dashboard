import pandas as pd
import streamlit as st

from lib import api, fmt

st.title("Drivers & vehicles")
tab_d, tab_v = st.tabs(["Drivers", "Vehicles"])

vehicles = api.safe(api.get, "/vehicles") or []
drivers = api.safe(api.get, "/drivers") or []
vlabel = {v["id"]: f"{v['reg_no']} ({v['vehicle_type']})" for v in vehicles}
taken = {d["vehicle"]["id"]: d["name"] for d in drivers if d["vehicle"]}

with tab_d:
    with st.expander("➕ Add driver"):
        with st.form("new_driver", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name *")
            phone = c2.text_input("Phone * (used for OTP login)")
            lic = c3.text_input("Licence no.")
            free = [None] + [v["id"] for v in vehicles if v["id"] not in taken and v["active"]]
            vid = st.selectbox("Vehicle", free, format_func=lambda x: "None" if x is None else vlabel[x])
            if st.form_submit_button("Add driver", type="primary"):
                if api.safe(api.post, "/drivers", {"name": name, "phone": phone, "license_no": lic or None,
                                                   "vehicle_id": vid}):
                    st.rerun()

    if drivers:
        st.dataframe(pd.DataFrame([{
            "ID": d["id"], "Name": d["name"], "Phone": d["phone"], "Licence": d["license_no"] or "",
            "Vehicle": d["vehicle"]["reg_no"] if d["vehicle"] else "–", "Active": d["active"],
            "Last location": fmt.ago(d["last_location"]["received_at"]) if d["last_location"] else "never",
        } for d in drivers]), hide_index=True, use_container_width=True)

        st.markdown("#### Edit driver / assign vehicle")
        dmap = {d["id"]: d for d in drivers}
        did = st.selectbox("Driver", list(dmap), format_func=lambda x: f"{dmap[x]['name']} ({dmap[x]['phone']})")
        d = dmap[did]
        with st.form(f"edit_driver_{did}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name", d["name"])
            lic = c2.text_input("Licence no.", d["license_no"] or "")
            current = d["vehicle"]["id"] if d["vehicle"] else -1
            opts = [-1] + [v["id"] for v in vehicles if v["id"] not in taken or v["id"] == current]
            vid = st.selectbox("Vehicle", opts, index=opts.index(current),
                               format_func=lambda x: "Unassigned" if x == -1 else vlabel[x])
            active = st.checkbox("Active", d["active"])
            if st.form_submit_button("Save"):
                body = {"name": name, "license_no": lic or None, "active": active}
                if vid != current:
                    body["vehicle_id"] = vid
                if api.safe(api.patch, f"/drivers/{did}", body):
                    st.rerun()
        st.caption("Drivers log in on their phone at <backend>/driver-app/ with their phone number + OTP.")

with tab_v:
    with st.expander("➕ Add vehicle"):
        with st.form("new_vehicle", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            reg = c1.text_input("Registration no. *")
            vtype = c2.selectbox("Type", ["truck", "mini-truck", "trailer", "container", "tempo"])
            cap = c3.number_input("Capacity (kg)", min_value=0.0, step=500.0)
            if st.form_submit_button("Add vehicle", type="primary"):
                if api.safe(api.post, "/vehicles", {"reg_no": reg.strip().upper(), "vehicle_type": vtype,
                                                    "capacity_kg": cap or None}):
                    st.rerun()
    if vehicles:
        st.dataframe(pd.DataFrame([{
            "ID": v["id"], "Registration": v["reg_no"], "Type": v["vehicle_type"], "Capacity (kg)": v["capacity_kg"],
            "Driver": taken.get(v["id"], "–"), "Active": v["active"],
        } for v in vehicles]), hide_index=True, use_container_width=True)
        vmap = {v["id"]: v for v in vehicles}
        c1, c2 = st.columns([3, 1])
        vid = c1.selectbox("Vehicle", list(vmap), format_func=vlabel.get, key="veh_toggle")
        label = "Deactivate" if vmap[vid]["active"] else "Activate"
        c2.write("")
        if c2.button(label, use_container_width=True):
            if api.safe(api.patch, f"/vehicles/{vid}", {"active": not vmap[vid]["active"]}):
                st.rerun()
