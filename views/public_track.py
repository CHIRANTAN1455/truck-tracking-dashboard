"""Public shipment tracking page for customers (no login, opened from the shared link)."""

import streamlit as st
from streamlit_folium import st_folium

from lib import api, fmt, maps


def render(token: str) -> None:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>",
                unsafe_allow_html=True)

    @st.fragment(run_every=15)
    def page() -> None:
        try:
            data = api.get(f"/public/track/{token}")
        except api.ApiError as exc:
            st.title("🚚 Shipment tracking")
            if exc.status in (404, 410):
                st.warning(exc.detail + ". Please ask the sender for a new link.")
            else:
                st.error("Tracking is temporarily unavailable. Please try again in a moment.")
            return

        shp = data["shipment"]
        st.title(f"🚚 Shipment {shp['id']}")
        st.subheader(fmt.status(data["status"]) if data["status"] != "BOOKED" else "Booked")

        c = st.columns(4)
        if data["status"] == "DELIVERED":
            c[0].metric("Delivered", fmt.local(data["delivered_at"]))
        else:
            c[0].metric("Estimated arrival", fmt.local(data["eta"]["eta"]) if data["eta"] else "–",
                        help=f"{data['eta']['remaining_km']} km remaining" if data["eta"] else None)
        c[1].metric("Last location update",
                    fmt.ago(data["location"]["ts"]) if data["location"] else "–",
                    help=fmt.local(data["last_update"]) if data["last_update"] else None)
        c[2].metric("Vehicle", data["vehicle_no"] or "–")
        c[3].metric("Expected by", fmt.local(data["expected_delivery_at"]))

        pick, drop = data["pickup"], data["drop"]
        pts = [(pick["lat"], pick["lon"]), (drop["lat"], drop["lon"])]
        if data["location"]:
            pts.append((data["location"]["lat"], data["location"]["lon"]))
        m = maps.base_map(pts)
        maps.place_marker(m, pick["lat"], pick["lon"], "pickup", pick["address"])
        maps.place_marker(m, drop["lat"], drop["lon"], "drop", drop["address"])
        if data["location"]:
            loc = data["location"]
            sim = loc.get("source") == "sim"
            if sim:
                maps.accuracy_circle(m, loc["lat"], loc["lon"], loc.get("accuracy_m"))
            maps.truck_marker(m, loc["lat"], loc["lon"],
                              maps.FRESHNESS_COLOR[maps.freshness(loc["age_sec"], 600 if sim else None)],
                              "Your shipment", {"Updated": fmt.local(loc["ts"])})
        st_folium(m, height=420, use_container_width=True, returned_objects=[], key="public_map")
        if data["location"] and data["location"].get("source") == "sim":
            st.caption(f"Approximate location from the mobile network (within "
                       f"{fmt.distance(data['location'].get('accuracy_m'))}). Updated every few minutes.")
        if not data["live_tracking"]:
            st.caption("Live location is shown only while the shipment is on the way."
                       if data["status"] != "DELIVERED" else "Live tracking has ended because the shipment was delivered.")

        left, right = st.columns(2)
        with left:
            st.markdown("#### Status")
            for step in data["timeline"]:
                mark = "✅" if step["done"] else "⚪"
                when = f" — {fmt.local(step['ts'])}" if step["ts"] else ""
                st.markdown(f"{mark} **{step['label']}**{when}")
        with right:
            st.markdown("#### Shipment details")
            st.markdown(f"**Shipment ID** {shp['id']}  \n"
                        + (f"**Reference** {shp['reference']}  \n" if shp["reference"] else "")
                        + f"**From** {pick['address']}  \n**To** {drop['address']}  \n"
                        + (f"**Goods** {shp['description']}  \n" if shp["description"] else "")
                        + (f"**Weight** {shp['weight_kg']:g} kg" if shp["weight_kg"] else ""))
        st.caption(f"This page refreshes automatically. Link valid until {fmt.local(data['link_expires_at'])}.")

    page()
