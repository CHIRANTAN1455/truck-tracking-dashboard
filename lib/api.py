"""Thin client for truck-tracking-backend. The session token is kept in st.session_state."""

import os

import requests
import streamlit as st



def _setting(name: str, default: str) -> str:
    """Environment variable, else Streamlit secret (Streamlit Community Cloud), else default."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return str(st.secrets[name])
    except Exception:  # no secrets.toml, or key missing
        return default


BACKEND_URL = _setting("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 60  # a free backend that was asleep needs up to ~50 s to wake up


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _headers() -> dict:
    token = st.session_state.get("token")
    return {"token": token} if token else {}


def request(method: str, path: str, **kwargs):
    try:
        r = requests.request(method, BACKEND_URL + path, headers=_headers(), timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(0, f"Backend not reachable at {BACKEND_URL}: {exc}") from exc
    if r.status_code == 401 and st.session_state.get("token"):
        st.session_state.pop("token", None)
        raise ApiError(401, "Session expired. Please log in again.")
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(r.status_code, str(detail))
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    return r.content


def get(path: str, **params):
    return request("GET", path, params={k: v for k, v in params.items() if v is not None})


def post(path: str, json: dict | None = None, **kwargs):
    return request("POST", path, json=json, **kwargs)


def patch(path: str, json: dict):
    return request("PATCH", path, json=json)


def safe(fn, *args, **kwargs):
    """Call the API and show errors inline instead of crashing the page. Returns None on error."""
    try:
        return fn(*args, **kwargs)
    except ApiError as exc:
        st.error(exc.detail)
        return None


def login(username: str, password: str) -> None:
    data = post("/auth/admin/login", {"username": username, "password": password})
    st.session_state["token"] = data["token"]


def logout() -> None:
    try:
        post("/auth/logout")
    except ApiError:
        pass
    st.session_state.pop("token", None)
