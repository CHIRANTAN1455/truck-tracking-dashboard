import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DISPLAY_TZ = ZoneInfo(os.environ.get("DISPLAY_TZ", "Asia/Kolkata"))

STATUS_LABELS = {
    "CREATED": "Created", "ASSIGNED": "Assigned", "PICKED_UP": "Picked up", "STARTED": "Trip started",
    "IN_TRANSIT": "In transit", "REACHED": "Reached destination", "DELIVERED": "Delivered",
    "CANCELLED": "Cancelled",
}
ALERT_LABELS = {"ROUTE_DEVIATION": "Route deviation", "DELAY": "Delivery delay",
                "LOCATION_STALE": "Location updates stopped"}


def parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def local(ts: str | None, with_date: bool = True) -> str:
    dt = parse(ts)
    if dt is None:
        return "–"
    return dt.astimezone(DISPLAY_TZ).strftime("%d %b %Y, %H:%M" if with_date else "%H:%M:%S")


def ago(ts: str | None) -> str:
    dt = parse(ts)
    if dt is None:
        return "never"
    sec = int((datetime.now(timezone.utc) - dt).total_seconds())
    if sec < 60:
        return f"{max(sec, 0)} s ago"
    if sec < 3600:
        return f"{sec // 60} min ago"
    if sec < 86400:
        return f"{sec // 3600} h {sec % 3600 // 60} min ago"
    return f"{sec // 86400} d ago"


def status(code: str | None) -> str:
    return STATUS_LABELS.get(code or "", code or "–")
