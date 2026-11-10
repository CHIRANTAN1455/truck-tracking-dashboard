"""Consent-based SIM tracking: who can be tracked, consent actions, pings and the audit trail."""

import pandas as pd
import streamlit as st

from lib import api, fmt

st.title("SIM tracking")

status = api.safe(api.get, "/sim/status")
if status is None:
    st.stop()
counts = status["counts"]
c = st.columns(6)
c[0].metric("Tracking", counts["ACTIVE"])
c[1].metric("Awaiting consent", counts["PENDING"])
c[2].metric("Withdrawn", counts["REVOKED"])
c[3].metric("Expired", counts["EXPIRED"])
c[4].metric("Failed", counts["FAILED"])
c[5].metric("Not registered", status["drivers_without_consent"])

with st.expander("Integration", expanded=status["provider"] == "mock"):
    st.markdown(
        f"**Provider** `{status['provider']}` · **Webhook** "
        f"{'enabled' if status['webhook_enabled'] else 'disabled (set SIM_WEBHOOK_SECRET)'} at "
        f"`{api.BACKEND_URL}{status['webhook_path']}`  \n"
        f"**Ping policy** every {status['ping_on_trip_min']:g} min on a trip, "
        + (f"every {status['ping_idle_min']:g} min when idle" if status["ping_idle_min"] else "idle drivers not pinged")
        + f" · consent SMS expires after {status['pending_consent_hours']:g} h without reply · "
        f"consent valid {status['consent_validity_days']:g} days")
    if status["provider"] == "mock":
        st.info("Running with the simulated provider. Consent SMS are not really sent; use "
                "**Simulate driver reply** below to play the driver's side.")
    if st.button("Run SIM poll now", help="Normally runs automatically every few seconds on the backend"):
        res = api.safe(api.post, "/sim/poll")
        if res:
            st.toast(f"Pinged {res['pinged']} · fixes {res['fixes']} · failed {res['failed']} · expired {res['expired']}")

companies = api.safe(api.get, "/companies") or []
cmap = {c["id"]: c for c in companies}
f1, f2 = st.columns(2)
cid = f1.selectbox("Company", [None] + list(cmap), format_func=lambda x: "All companies" if x is None else cmap[x]["name"])
sfilter = f2.selectbox("Consent status", [None, "ACTIVE", "PENDING", "REVOKED", "EXPIRED", "FAILED"],
                       format_func=lambda x: "Any" if x is None else fmt.sim_status(x))

rows = api.safe(api.get, "/sim/consents", company_id=cid, status=sfilter) or []
if rows:
    df = pd.DataFrame([{
        "Driver ID": r["driver"]["id"], "Driver": r["driver"]["name"], "Mobile": r["driver"]["phone"],
        "Company": r["company"]["code"] if r["company"] else "–", "Operator": r["operator"] or "–",
        "Status": fmt.sim_status(r["status"]), "Ping every": f"{r['ping_interval_min']:g} min",
        "Last fix": fmt.ago(r["last_fix_at"]) if r["last_fix_at"] else "never",
        "Consent since": fmt.local(r["activated_at"]) if r["activated_at"] else "–",
        "Valid until": fmt.local(r["expires_at"]) if r["expires_at"] else "–",
        "Problem": r["last_error"] or "",
    } for r in rows])
    sel = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun",
                       selection_mode="single-row", key="sim_table")
    picked = rows[sel.selection.rows[0]] if sel.selection.rows else None
else:
    st.info("No SIM registrations match this filter.")
    picked = None

b1, b2 = st.columns(2)
label = f"Send consent SMS to all unregistered drivers{' of ' + cmap[cid]['name'] if cid else ''}"
if b1.button(label, use_container_width=True):
    res = api.safe(api.post, "/sim/consents/bulk-request", {"company_id": cid})
    if res:
        st.toast(f"Consent requested for {res['requested']} driver(s)")
        st.rerun()

if picked:
    st.divider()
    d = picked["driver"]
    st.subheader(f"{d['name']} · {d['phone']}")
    st.caption(f"{fmt.sim_status(picked['status'])} · operator {picked['operator'] or 'unknown'} · "
               f"provider ref {picked.get('provider_ref') or '–'}")
    a = st.columns(4)
    if a[0].button("📍 Locate now", disabled=picked["status"] != "ACTIVE", use_container_width=True):
        res = api.safe(api.post, f"/drivers/{d['id']}/sim/locate")
        if res:
            if res["ok"]:
                st.success(f"Located at {res['fix']['lat']:.4f}, {res['fix']['lon']:.4f} "
                           f"(±{fmt.distance(res['fix']['accuracy_m'])})")
            else:
                st.warning(res["error"])
    if a[1].button("✉️ Re-send consent SMS", disabled=picked["status"] in ("ACTIVE", "PENDING"),
                   use_container_width=True):
        if api.safe(api.post, f"/drivers/{d['id']}/sim/consent"):
            st.rerun()
    if a[2].button("⛔ Stop tracking", disabled=picked["status"] not in ("ACTIVE", "PENDING"),
                   use_container_width=True):
        if api.safe(api.post, f"/drivers/{d['id']}/sim/revoke"):
            st.rerun()
    if status["provider"] == "mock" and picked["status"] == "PENDING":
        with a[3].popover("Simulate driver reply", use_container_width=True):
            reply = st.radio("Driver replies", ["Y", "N"], horizontal=True)
            if st.button("Send reply"):
                if api.safe(api.post, "/integrations/sim/mock/reply", {"phone": d["phone"], "reply": reply}):
                    st.rerun()

    events = api.safe(api.get, "/sim/events", driver_id=d["id"]) or []
    if events:
        st.markdown("#### Consent history (audit trail)")
        st.dataframe(pd.DataFrame([{"Time": fmt.local(e["created_at"]), "Event": e["kind"], "Detail": e["detail"] or ""}
                                   for e in events]), hide_index=True, use_container_width=True)

st.caption("Drivers are located through their SIM only after they reply YES to the consent SMS. "
           "They can withdraw at any time (reply STOP to the provider, or ops can stop tracking here); "
           "locations are never stored without active consent.")
