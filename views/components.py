"""Widgets shared between pages."""

import pandas as pd
import streamlit as st

from lib import api, fmt


def tracking_links(shipment_id: str) -> None:
    st.markdown("#### Customer tracking link")
    shp = api.safe(api.get, f"/shipments/{shipment_id}")
    if shp is None:
        return
    links = shp["tracking_links"]
    active = next((link for link in links if link["state"] == "active"), None)

    if active:
        st.code(active["share"]["url"], language=None)
        c = st.columns(4)
        c[0].link_button("Share on WhatsApp", active["share"]["whatsapp"], use_container_width=True)
        c[1].link_button("Send SMS", active["share"]["sms"], use_container_width=True)
        c[2].link_button("Send email", active["share"]["email"], use_container_width=True)
        if c[3].button("Revoke link", key=f"revoke_{active['token']}", use_container_width=True):
            if api.safe(api.post, f"/tracking-links/{active['token']}/revoke"):
                st.rerun()
        st.caption(f"Expires {fmt.local(active['expires_at'])}")
    else:
        st.caption("No active tracking link. One is created automatically when the trip starts.")

    with st.popover("New tracking link"):
        hours = st.number_input("Valid for (hours)", min_value=1, max_value=24 * 90, value=168,
                                key=f"ttl_{shipment_id}")
        if st.button("Generate", key=f"gen_{shipment_id}"):
            if api.safe(api.post, f"/shipments/{shipment_id}/tracking-links", {"ttl_hours": int(hours)}):
                st.rerun()

    if len(links) > 1 or (links and not active):
        with st.expander(f"All links ({len(links)})"):
            st.dataframe(pd.DataFrame([{"State": link["state"], "Created": fmt.local(link["created_at"]),
                                        "Expires": fmt.local(link["expires_at"]), "URL": link["share"]["url"]}
                                       for link in links]), hide_index=True, use_container_width=True)
