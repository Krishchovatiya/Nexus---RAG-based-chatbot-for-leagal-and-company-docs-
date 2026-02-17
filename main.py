"""
main.py
Nexus Enterprise Bot — Application Entry Point.

Starts a pure-Python HTTP server (no framework needed).
Run with:  python main.py

Open browser at: http://127.0.0.1:8000
"""

import sys
import signal
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import config
from modules.router import route_get, route_post


# ── Request Handler ───────────────────────────────────────────────────────────

class NexusHandler(BaseHTTPRequestHandler):
    """Thin wrapper that delegates to the router module."""

    def do_GET(self) -> None:
        try:
            route_get(self, self.path)
        except BrokenPipeError:
            pass  # Client disconnected — normal

    def do_POST(self) -> None:
        try:
            route_post(self, self.path)
        except BrokenPipeError:
            pass

    def log_message(self, fmt: str, *args) -> None:
        # Suppress request logs for cleaner output; re-enable if debugging
        method = args[0] if args else ""
        status = args[1] if len(args) > 1 else ""
        if not self.path.startswith("/static/"):
            print(f"  {method}  →  {status}")


# ── Server ────────────────────────────────────────────────────────────────────

def run() -> None:
    server_address = (config.HOST, config.PORT)

    try:
        httpd = HTTPServer(server_address, NexusHandler)
    except OSError as exc:
        print(f"\n❌ Could not start server on {config.HOST}:{config.PORT}")
        print(f"   {exc}")
        print(f"   Try changing PORT in config.py\n")
        sys.exit(1)

    url = f"http://{config.HOST}:{config.PORT}"

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║       Nexus Enterprise Intelligence Bot       ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  ⚡  Model   :  {config.MODEL}")
    print(f"  🌐  Running :  {url}")
    print(f"  🔑  Get key :  https://openrouter.ai/keys (free)")
    print()
    print("  Press Ctrl+C to stop")
    print()

    # Auto-open browser (best-effort)
    def _open_browser():
        import webbrowser
        webbrowser.open(url)

    timer = threading.Timer(0.8, _open_browser)
    timer.daemon = True
    timer.start()

    # Graceful shutdown on Ctrl+C
    def _shutdown(sig, frame):
        print("\n\n  Shutting down Nexus… goodbye.\n")
        httpd.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)

    httpd.serve_forever()


if __name__ == "__main__":
    run()
