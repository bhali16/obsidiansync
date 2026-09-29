"""Flask HTTP server exposing pairing, manifest and file-download endpoints for the Android client."""
import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from werkzeug.serving import make_server

import vault_sync

logging.getLogger("werkzeug").setLevel(logging.WARNING)


class SyncServer:
    def __init__(self, state):
        """state: a shared AppState-like object with .token, .vault_path, .device_name, .on_event(name, **kw)."""
        self.state = state
        self.app = Flask(__name__)
        self._register_routes()
        self._server = None
        self._sync_total = 0
        self._sync_done = 0

    def _check_token(self) -> bool:
        token = request.args.get("token") or request.headers.get("X-Auth-Token")
        return token == self.state.token

    def _register_routes(self):
        app = self.app

        @app.get("/pair")
        def pair():
            if not self._check_token():
                return jsonify({"error": "invalid token"}), 403
            self.state.on_event("device_connected", client_ip=request.remote_addr)
            return jsonify(
                {
                    "status": "ok",
                    "device_name": self.state.device_name,
                }
            )

        @app.get("/manifest")
        def manifest():
            if not self._check_token():
                return jsonify({"error": "invalid token"}), 403
            if not self.state.vault_path:
                return jsonify({"error": "no vault configured"}), 400
            files = vault_sync.build_manifest(self.state.vault_path)
            self.state.on_event("sync_started", client_ip=request.remote_addr)
            return jsonify({"vault_name": Path(self.state.vault_path).name, "files": files})

        @app.get("/sync-begin")
        def sync_begin():
            if not self._check_token():
                return jsonify({"error": "invalid token"}), 403
            self._sync_total = request.args.get("total", type=int, default=0)
            self._sync_done = 0
            self.state.on_event(
                "sync_progress", client_ip=request.remote_addr,
                done=0, total=self._sync_total,
            )
            return jsonify({"status": "ok"})

        @app.get("/sync-complete")
        def sync_complete():
            if not self._check_token():
                return jsonify({"error": "invalid token"}), 403
            self.state.on_event(
                "sync_finished",
                client_ip=request.remote_addr,
                status=request.args.get("status", "success"),
                updated=request.args.get("updated", type=int, default=0),
                deleted=request.args.get("deleted", type=int, default=0),
                message=request.args.get("message", ""),
            )
            return jsonify({"status": "ok"})

        @app.get("/file")
        def file():
            if not self._check_token():
                return jsonify({"error": "invalid token"}), 403
            rel_path = request.args.get("path", "")
            resolved = vault_sync.resolve_file(self.state.vault_path, rel_path)
            if resolved is None:
                return jsonify({"error": "not found"}), 404
            if self._sync_total:
                self._sync_done += 1
                self.state.on_event(
                    "sync_progress", client_ip=request.remote_addr,
                    done=self._sync_done, total=self._sync_total,
                )
            return send_file(resolved, as_attachment=True, download_name=resolved.name)

        @app.get("/health")
        def health():
            return jsonify({"status": "ok"})

    def start(self, host: str, port: int):
        self._server = make_server(host, port, self.app)
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.shutdown()
