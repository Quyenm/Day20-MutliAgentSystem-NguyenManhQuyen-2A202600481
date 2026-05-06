"""Small stdlib HTTP server for the localhost demo."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from multi_agent_research_lab.web.backend import build_demo_payload

ASSET_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def load_frontend_asset(name: str) -> str:
    """Load a packaged frontend asset by name."""

    asset = files("multi_agent_research_lab.web.frontend").joinpath(name)
    return asset.read_text(encoding="utf-8")


def create_handler() -> type[BaseHTTPRequestHandler]:
    """Return a request handler bound to the demo backend."""

    class DemoRequestHandler(BaseHTTPRequestHandler):
        server_version = "MultiAgentResearchLabWeb/1.0"

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send_text(load_frontend_asset("index.html"), "text/html; charset=utf-8")
                return
            if path.startswith("/assets/"):
                self._serve_asset(path.removeprefix("/assets/"))
                return
            if path == "/api/last":
                self._send_last_run()
                return
            self._send_error(HTTPStatus.NOT_FOUND, "Route not found")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/run":
                self._send_error(HTTPStatus.NOT_FOUND, "Route not found")
                return
            try:
                body = self._read_json()
                payload = build_demo_payload(str(body.get("query", "")))
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except Exception as exc:  # pragma: no cover - protects live demo requests.
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"{type(exc).__name__}: {exc}")
                return
            self._send_json(payload)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _serve_asset(self, name: str) -> None:
            suffix = Path(name).suffix
            if suffix not in ASSET_TYPES:
                self._send_error(HTTPStatus.NOT_FOUND, "Unsupported asset")
                return
            try:
                content = load_frontend_asset(name)
            except FileNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "Asset not found")
                return
            self._send_text(content, ASSET_TYPES[suffix])

        def _send_last_run(self) -> None:
            path = Path("reports/web_demo_last_run.json")
            if not path.exists():
                self._send_error(HTTPStatus.NOT_FOUND, "No web demo run has been recorded yet")
                return
            self._send_text(path.read_text(encoding="utf-8"), "application/json; charset=utf-8")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            if not raw:
                return {}
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object.")
            return data

        def _send_json(self, payload: dict[str, Any]) -> None:
            self._send_text(json.dumps(payload), "application/json; charset=utf-8")

        def _send_text(self, content: str, content_type: str) -> None:
            encoded = content.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            payload = json.dumps({"error": message}).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return DemoRequestHandler


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local web server until interrupted."""

    server = ThreadingHTTPServer((host, port), create_handler())
    try:
        server.serve_forever()
    finally:
        server.server_close()

