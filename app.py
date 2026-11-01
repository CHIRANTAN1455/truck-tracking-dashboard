"""Truck tracking dashboard.

  * `/?track=<token>`  -> public customer tracking page (no login)
  * everything else   -> operations dashboard (admin login)
"""

import streamlit as st

from lib import api

st.set_page_config(page_title="Truck Tracking", page_icon="🚚", layout="wide")

if "track" in st.query_params:
    from views import public_track

    public_track.render(st.query_params["track"])
    st.stop()


def login_page() -> None:
    st.title("🚚 Truck Tracking")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in", type="primary"):
            try:
                api.login(username, password)
                st.rerun()
            except api.ApiError as exc:
                st.error(exc.detail)


if not st.session_state.get("token"):
    login_page()
    st.stop()

pages = {
    "Operations": [
        st.Page("views/live_map.py", title="Live map", icon="🗺️", default=True),
        st.Page("views/trips.py", title="Trips", icon="🛣️"),
        st.Page("views/shipments.py", title="Shipments", icon="📦"),
        st.Page("views/alerts.py", title="Alerts", icon="🚨"),
    ],
    "Fleet": [
        st.Page("views/fleet.py", title="Drivers & vehicles", icon="👷"),
        st.Page("views/history.py", title="Location history", icon="🕒"),
    ],
    "Reports": [
        st.Page("views/reports.py", title="Trip reports", icon="📊"),
        st.Page("views/notifications.py", title="Notifications", icon="✉️"),
    ],
}
nav = st.navigation(pages)
with st.sidebar:
    st.caption(f"Backend: {api.BACKEND_URL}")
    if st.button("Log out"):
        api.logout()
        st.rerun()
nav.run()
