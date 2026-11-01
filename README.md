# truck-tracking-dashboard

Streamlit operations dashboard and public customer tracking page for
[truck-tracking-backend](../truck-tracking-backend).

The live map is a port of [nammayatri/tracking-dashboard](https://github.com/nammayatri/tracking-dashboard)
(React/Leaflet): freshness-coloured markers (green < 1 min, orange 1–5 min, red > 5 min), summary
cards, hover tooltips / click popups, 10 s auto-refresh, and trail playback for location history.

## Run

```sh
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
BACKEND_URL=http://localhost:8000 .venv/bin/streamlit run app.py
```

Open http://localhost:8501 and log in with the backend's `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

| Env var | Default | |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | truck-tracking-backend URL |
| `DISPLAY_TZ` | `Asia/Kolkata` | Time zone for displayed times |

Set the backend's `PUBLIC_TRACKING_BASE_URL` to this dashboard's public URL so shared links point here.

## Pages

| Page | What it does |
|---|---|
| Live map | All trucks, colour by last-update age, popups with driver / trip / speed / last update |
| Trips | Active / completed / cancelled tabs, create trip, assign driver + vehicle, status actions, cancel, POD (photo, receiver, OTP), timeline, trip map (planned route + travelled path), tracking link share/revoke |
| Shipments | Create shipments (pickup & destination), details, tracking links |
| Alerts | Route deviation, delivery delay, location stopped; resolve; run checks now |
| Drivers & vehicles | Driver profiles, vehicle assignment, activate/deactivate |
| Location history | Per trip or per driver + date range, playback slider, CSV export |
| Trip reports | Distance, duration, on-time %, by status, CSV export |
| Notifications | Customer and ops message log |
| `/?track=<token>` | **Public** tracking page: live map, ETA, last update, status timeline, shipment details. No login; stops showing location after delivery; expired / revoked links show a message |
