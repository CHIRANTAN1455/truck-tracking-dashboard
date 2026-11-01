import pandas as pd
import streamlit as st

from lib import api, fmt

st.title("Notifications")
st.caption("Trip start / delivery messages to customers and alert messages to operations. "
           "'logged' means no SMS/WhatsApp/SMTP provider is configured on the backend yet.")

trip_id = st.text_input("Filter by trip ID").strip() or None
rows = api.safe(api.get, "/notifications", trip_id=trip_id) or []
if not rows:
    st.info("No notifications yet.")
else:
    st.dataframe(pd.DataFrame([{"Time": fmt.local(n["created_at"]), "Channel": n["channel"],
                                "To": n["recipient"] or "", "Trip": n["trip_id"] or "", "Status": n["status"],
                                "Message": n["message"]} for n in rows]),
                 hide_index=True, use_container_width=True)
