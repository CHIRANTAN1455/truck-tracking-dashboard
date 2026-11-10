import streamlit as st

from lib import api, fmt

st.title("Alerts")

companies = api.safe(api.get, "/companies") or []
cmap = {c["id"]: c for c in companies}
c0, c1, c2 = st.columns([2, 2, 1])
cid = c0.selectbox("Company", [None] + list(cmap), format_func=lambda x: "All companies" if x is None else cmap[x]["name"])
show_all = c1.toggle("Include resolved alerts", value=False)
if c2.button("Run checks now", use_container_width=True,
             help="Delay and stale-location checks normally run every minute on the backend"):
    res = api.safe(api.post, "/alerts/run-checks")
    if res:
        st.toast(f"Checked {res['checked_trips']} active trip(s)")


@st.fragment(run_every=30)
def alert_list() -> None:
    alerts = api.safe(api.get, "/alerts", open_only=not show_all, company_id=cid) or []
    if not alerts:
        st.success("No alerts. All trucks are reporting and on schedule.")
        return
    icons = {"ROUTE_DEVIATION": "🧭", "DELAY": "⏰", "LOCATION_STALE": "📡"}
    for a in alerts:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"{icons.get(a['kind'], '⚠️')} **{fmt.ALERT_LABELS.get(a['kind'], a['kind'])}** · "
                        f"trip `{a['trip_id']}` · {fmt.local(a['created_at'])} ({fmt.ago(a['created_at'])})  \n"
                        f"{a['message']}")
            if a["resolved_at"]:
                c2.caption(f"Resolved {fmt.local(a['resolved_at'])}")
            elif c2.button("Resolve", key=f"res_{a['id']}", use_container_width=True):
                api.safe(api.post, f"/alerts/{a['id']}/resolve")
                st.rerun(scope="fragment")


alert_list()
