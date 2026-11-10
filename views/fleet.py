import pandas as pd
import streamlit as st

from lib import api, fmt

st.title("Companies, drivers & vehicles")
tab_c, tab_d, tab_v = st.tabs(["Companies", "Drivers", "Vehicles"])

companies = api.safe(api.get, "/companies") or []
cmap = {c["id"]: c for c in companies}
clabel = {None: "No company"} | {c["id"]: f"{c['name']} ({c['code']})" for c in companies}

with tab_c:
    with st.expander("➕ Add trucking company"):
        with st.form("new_company", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            code = c1.text_input("Code * (short, e.g. VFC)")
            name = c2.text_input("Company name *")
            gstin = c3.text_input("GSTIN")
            c4, c5, c6 = st.columns(3)
            contact = c4.text_input("Contact person")
            cphone = c5.text_input("Contact phone")
            email = c6.text_input("Contact email")
            c7, c8, c9 = st.columns(3)
            city = c7.text_input("Hub city")
            hlat = c8.number_input("Hub latitude", value=0.0, format="%.5f")
            hlon = c9.number_input("Hub longitude", value=0.0, format="%.5f")
            if st.form_submit_button("Add company", type="primary"):
                body = {"code": code.strip().upper(), "name": name.strip(), "gstin": gstin.strip().upper() or None,
                        "contact_name": contact or None, "contact_phone": cphone or None,
                        "contact_email": email or None, "hub_city": city or None,
                        "hub_lat": hlat or None, "hub_lon": hlon or None}
                if api.safe(api.post, "/companies", body):
                    st.rerun()
    if companies:
        st.dataframe(pd.DataFrame([{
            "Code": c["code"], "Company": c["name"], "Hub": c["hub_city"] or "–", "GSTIN": c["gstin"] or "–",
            "Drivers": c["counts"]["drivers"], "Vehicles": c["counts"]["vehicles"],
            "On trip": c["counts"]["on_trip"], "SIM tracking": c["counts"]["sim_active"],
            "Contact": " · ".join(x for x in (c["contact_name"], c["contact_phone"], c["contact_email"]) if x) or "–",
            "Active": c["active"],
        } for c in companies]), hide_index=True, use_container_width=True)
    else:
        st.info("No companies yet. Add the trucking companies whose drivers you track.")

vehicles = api.safe(api.get, "/vehicles") or []
drivers = api.safe(api.get, "/drivers") or []
vlabel = {v["id"]: f"{v['reg_no']} ({v['vehicle_type']})" for v in vehicles}
taken = {d["vehicle"]["id"]: d["name"] for d in drivers if d["vehicle"]}


def free_vehicles(company_id, current=None):
    return [v["id"] for v in vehicles if v["active"] and (v["id"] not in taken or v["id"] == current)
            and (company_id is None or v["company_id"] in (None, company_id))]


with tab_d:
    with st.expander("➕ Add driver"):
        st.caption("Adding a driver sends them the SIM tracking consent SMS. Tracking starts when they reply YES.")
        new_cid = st.selectbox("Company", list(clabel), format_func=clabel.get, key="new_driver_company")
        with st.form("new_driver", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name *")
            phone = c2.text_input("Mobile number * (the SIM that is tracked)", placeholder="98450 00001")
            lic = c3.text_input("Licence no.")
            vid = st.selectbox("Vehicle", [None] + free_vehicles(new_cid),
                               format_func=lambda x: "None" if x is None else vlabel[x])
            if st.form_submit_button("Add driver", type="primary"):
                if api.safe(api.post, "/drivers", {"name": name, "phone": phone, "license_no": lic or None,
                                                   "company_id": new_cid, "vehicle_id": vid}):
                    st.rerun()

    fc = st.selectbox("Show drivers of", [0] + list(cmap),
                      format_func=lambda x: "All companies" if x == 0 else cmap[x]["name"], key="driver_filter")
    shown = [d for d in drivers if fc == 0 or (d["company"] and d["company"]["id"] == fc)]
    if shown:
        st.dataframe(pd.DataFrame([{
            "ID": d["id"], "Name": d["name"], "Mobile": d["phone"],
            "Company": d["company"]["code"] if d["company"] else "–", "Licence": d["license_no"] or "",
            "Vehicle": d["vehicle"]["reg_no"] if d["vehicle"] else "–",
            "SIM tracking": fmt.sim_status(d["sim"]["status"] if d["sim"] else None),
            "Operator": (d["sim"] or {}).get("operator") or "–", "Active": d["active"],
            "Last location": fmt.ago(d["last_location"]["received_at"]) if d["last_location"] else "never",
        } for d in shown]), hide_index=True, use_container_width=True)
        st.caption(f"{len(shown)} driver(s)")

        st.markdown("#### Edit driver / assign vehicle")
        dmap = {d["id"]: d for d in shown}
        did = st.selectbox("Driver", list(dmap), format_func=lambda x: f"{dmap[x]['name']} ({dmap[x]['phone']})")
        d = dmap[did]
        with st.form(f"edit_driver_{did}"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name", d["name"])
            lic = c2.text_input("Licence no.", d["license_no"] or "")
            cur_cid = d["company"]["id"] if d["company"] else None
            cid = c3.selectbox("Company", list(clabel), index=list(clabel).index(cur_cid), format_func=clabel.get)
            current = d["vehicle"]["id"] if d["vehicle"] else -1
            opts = [-1] + free_vehicles(cur_cid, current)
            vid = st.selectbox("Vehicle", opts, index=opts.index(current) if current in opts else 0,
                               format_func=lambda x: "Unassigned" if x == -1 else vlabel[x])
            active = st.checkbox("Active", d["active"])
            if st.form_submit_button("Save"):
                body = {"name": name, "license_no": lic or None, "active": active}
                if cid != cur_cid and cid is not None:
                    body["company_id"] = cid
                if vid != current:
                    body["vehicle_id"] = vid
                if api.safe(api.patch, f"/drivers/{did}", body):
                    st.rerun()
        st.caption("Location comes from the driver's SIM (see the SIM tracking page). The phone app at "
                   "<backend>/driver-app/ is optional and adds precise GPS when the driver uses it.")
    else:
        st.info("No drivers.")

with tab_v:
    with st.expander("➕ Add vehicle"):
        with st.form("new_vehicle", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            reg = c1.text_input("Registration no. *")
            vtype = c2.selectbox("Type", ["truck", "mini-truck", "trailer", "container", "tempo"])
            cap = c3.number_input("Capacity (kg)", min_value=0.0, step=500.0)
            vcid = c4.selectbox("Company", list(clabel), format_func=clabel.get)
            if st.form_submit_button("Add vehicle", type="primary"):
                if api.safe(api.post, "/vehicles", {"reg_no": reg.strip().upper().replace(" ", ""),
                                                    "vehicle_type": vtype, "capacity_kg": cap or None,
                                                    "company_id": vcid}):
                    st.rerun()
    fv = st.selectbox("Show vehicles of", [0] + list(cmap),
                      format_func=lambda x: "All companies" if x == 0 else cmap[x]["name"], key="veh_filter")
    vshown = [v for v in vehicles if fv == 0 or v["company_id"] == fv]
    if vshown:
        st.dataframe(pd.DataFrame([{
            "ID": v["id"], "Registration": v["reg_no"], "Type": v["vehicle_type"], "Capacity (kg)": v["capacity_kg"],
            "Company": cmap[v["company_id"]]["code"] if v["company_id"] in cmap else "–",
            "Driver": taken.get(v["id"], "–"), "Active": v["active"],
        } for v in vshown]), hide_index=True, use_container_width=True)
        vmap = {v["id"]: v for v in vshown}
        c1, c2 = st.columns([3, 1])
        vid = c1.selectbox("Vehicle", list(vmap), format_func=vlabel.get, key="veh_toggle")
        label = "Deactivate" if vmap[vid]["active"] else "Activate"
        c2.write("")
        if c2.button(label, use_container_width=True):
            if api.safe(api.patch, f"/vehicles/{vid}", {"active": not vmap[vid]["active"]}):
                st.rerun()
