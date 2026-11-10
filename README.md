# truck-tracking-dashboard

Streamlit operations dashboard and public customer tracking page for
[truck-tracking-backend](../truck-tracking-backend).

Trucks are located through the driver's SIM (consent-based network location, see the backend README).
SIM fixes are approximate, so maps draw them as a circle around the truck, and freshness is judged against
each truck's ping interval (10 min on a trip) instead of a fixed 1 / 5 minutes.

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
| Live map | All trucks, filter by company (one map layer per company), SIM accuracy circles, colour by "on schedule" vs each truck's ping interval, per-company summary |
| Trips | Active / completed / cancelled tabs, create trip, assign driver + vehicle, status actions, cancel, POD (photo, receiver, OTP), timeline, trip map (planned route + travelled path), tracking link share/revoke |
| Shipments | Create shipments (pickup & destination), details, tracking links |
| Alerts | Route deviation, delivery delay, location stopped; resolve; run checks now |
| Companies & drivers | Trucking companies (counts, SIM coverage), drivers with company + SIM status, vehicles per company |
| SIM tracking | Consent status per driver (tracking / awaiting / withdrawn / expired / failed), locate now, re-send or stop consent, bulk consent per company, consent audit trail, integration health |
| Location history | Per trip or per driver + date range, playback slider, CSV export |
| Trip reports | Distance, duration, on-time %, by status, CSV export |
| Notifications | Customer and ops message log |
| `/?track=<token>` | **Public** tracking page: live map, ETA, last update, status timeline, shipment details. No login; stops showing location after delivery; expired / revoked links show a message |
