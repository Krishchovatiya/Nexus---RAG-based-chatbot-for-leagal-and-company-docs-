"""
modules/router.py
HTTP request router — maps URL paths to handler functions.
All endpoint logic lives here; the server in main.py just delegates here.
"""

from __future__ import annotations
import json
import cgi
import io
import os
import pathlib
import mimetypes
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import config
from modules.document_store import store
from modules import llm_client

# Per-session conversation history (single-user; keyed by a simple cookie)
_conversations: dict[str, list[dict]] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json_response(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(handler: BaseHTTPRequestHandler, message: str, status: int = 400) -> None:
    _json_response(handler, {"ok": False, "error": message}, status)


def _ok(handler: BaseHTTPRequestHandler, data: dict | None = None) -> None:
    _json_response(handler, {"ok": True, **(data or {})})


def _get_session_id(handler: BaseHTTPRequestHandler) -> str:
    """Extract or create a simple session ID from Cookie header."""
    cookie = handler.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("nexus_session="):
            return part.split("=", 1)[1]
    return "default"


def _serve_static(handler: BaseHTTPRequestHandler, path: str) -> None:
    """Serve a file from the project directory."""
    # Map URL path to filesystem path
    base = pathlib.Path(__file__).resolve().parent.parent
    file_path = base / path.lstrip("/")

    if not file_path.exists() or not file_path.is_file():
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Not found")
        return

    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"

    content = file_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


# ── GET Routes ────────────────────────────────────────────────────────────────

def route_get(handler: BaseHTTPRequestHandler, path: str) -> None:
    parsed = urlparse(path)
    clean  = parsed.path.rstrip("/") or "/"

    # ── Index ──────────────────────────────────────────────────────────
    if clean == "/":
        _serve_static(handler, "templates/index.html")

    # ── Static assets ──────────────────────────────────────────────────
    elif clean.startswith("/static/"):
        _serve_static(handler, clean)

    # ── Document list ──────────────────────────────────────────────────
    elif clean == "/api/documents":
        _ok(handler, {
            "documents": store.to_list(),
            "ingested":  store.is_ingested,
            "count":     len(store.documents),
        })

    # ── Mode list ──────────────────────────────────────────────────────
    elif clean == "/api/modes":
        modes = {
            k: {"label": v["label"], "chips": v["chips"]}
            for k, v in config.MODES.items()
        }
        _ok(handler, {"modes": modes})

    # ── Health check ───────────────────────────────────────────────────
    elif clean == "/api/health":
        _ok(handler, {"model": config.MODEL, "status": "online"})

    else:
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Not found")


# ── POST Routes ───────────────────────────────────────────────────────────────

def route_post(handler: BaseHTTPRequestHandler, path: str) -> None:
    parsed = urlparse(path)
    clean  = parsed.path.rstrip("/")

    # ── Upload document ────────────────────────────────────────────────
    if clean == "/api/upload":
        _handle_upload(handler)

    # ── Remove document ────────────────────────────────────────────────
    elif clean == "/api/remove":
        body = _read_json(handler)
        if body is None:
            return
        name = body.get("name", "").strip()
        if not name:
            _error(handler, "Missing 'name' field")
            return
        ok, msg = store.remove(name)
        if ok:
            _ok(handler, {"message": msg, "documents": store.to_list()})
        else:
            _error(handler, msg)

    # ── Ingest documents ───────────────────────────────────────────────
    elif clean == "/api/ingest":
        ok, msg = store.ingest()
        if ok:
            _ok(handler, {"message": msg, "ingested": True})
        else:
            _error(handler, msg)

    # ── Chat ───────────────────────────────────────────────────────────
    elif clean == "/api/chat":
        _handle_chat(handler)

    # ── Clear conversation ─────────────────────────────────────────────
    elif clean == "/api/clear":
        session = _get_session_id(handler)
        _conversations[session] = []
        _ok(handler, {"message": "Conversation cleared"})

    else:
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"Not found")


# ── Upload Handler ────────────────────────────────────────────────────────────

def _handle_upload(handler: BaseHTTPRequestHandler) -> None:
    content_type = handler.headers.get("Content-Type", "")
    length       = int(handler.headers.get("Content-Length", 0))

    if "multipart/form-data" not in content_type:
        _error(handler, "Expected multipart/form-data")
        return

    raw_body = handler.rfile.read(length)

    # Parse multipart manually using cgi module
    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE":   content_type,
        "CONTENT_LENGTH": str(length),
    }
    try:
        form = cgi.FieldStorage(
            fp=io.BytesIO(raw_body),
            environ=environ,
            keep_blank_values=True,
        )
    except Exception as exc:
        _error(handler, f"Failed to parse upload: {exc}")
        return

    results = []
    files = form["file"] if "file" in form else []

    # Normalise to list
    if not isinstance(files, list):
        files = [files]

    for item in files:
        if not hasattr(item, "filename") or not item.filename:
            continue
        name = os.path.basename(item.filename)
        data = item.file.read()
        ok, msg = store.add(name, data)
        results.append({"name": name, "ok": ok, "message": msg})

    if not results:
        _error(handler, "No files received")
        return

    _ok(handler, {
        "results":   results,
        "documents": store.to_list(),
    })


# ── Chat Handler ──────────────────────────────────────────────────────────────

def _handle_chat(handler: BaseHTTPRequestHandler) -> None:
    body = _read_json(handler)
    if body is None:
        return

    api_key = (body.get("api_key") or "").strip()
    query   = (body.get("query") or "").strip()
    mode    = (body.get("mode") or config.DEFAULT_MODE).strip()

    if not api_key:
        _error(handler, "Missing API key")
        return
    if not query:
        _error(handler, "Missing query")
        return
    if mode not in config.MODES:
        mode = config.DEFAULT_MODE

    session = _get_session_id(handler)
    history = _conversations.setdefault(session, [])

    # Append user message to history
    history.append({"role": "user", "content": query})

    try:
        reply = llm_client.chat(
            api_key=api_key,
            messages=history,
            mode=mode,
            knowledge_base=store.knowledge_base,
        )
        history.append({"role": "assistant", "content": reply})

        _ok(handler, {
            "reply":   reply,
            "mode":    mode,
            "history_length": len(history),
        })

    except (ValueError, RuntimeError) as exc:
        # Roll back user message on failure
        history.pop()
        _error(handler, str(exc))

    except Exception as exc:
        history.pop()
        _error(handler, f"Unexpected error: {exc}", status=500)


# ── Body Reader ───────────────────────────────────────────────────────────────

def _read_json(handler: BaseHTTPRequestHandler) -> dict | None:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        _error(handler, "Empty request body")
        return None
    try:
        raw  = handler.rfile.read(length)
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        _error(handler, f"Invalid JSON: {exc}")
        return None
