"""Small paired HTTP receiver for Steam Deck clips. Python standard library only."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import socket
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_UPLOAD = 20 * 1024**3


def _config_token(config_path: Path) -> str:
    if config_path.is_file():
        token = json.loads(config_path.read_text())["token"]
        if isinstance(token, str) and len(token) >= 32:
            return token
        raise ValueError("Receiver config contains an invalid token")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump({"token": token}, out)
    return token


class ClipReceiver(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, destination: Path, config_path: Path, plugin_zip: Path | None = None):
        self.destination = destination.expanduser().resolve()
        self.destination.mkdir(parents=True, exist_ok=True)
        self.token = _config_token(config_path.expanduser())
        self.pair_code = f"{secrets.randbelow(1_000_000):06d}"
        self.pair_deadline = time.monotonic() + 15 * 60
        self.failed_pairs: dict[str, tuple[int, float]] = {}
        self.receiver_name = socket.gethostname().split(".")[0]
        self.plugin_zip = plugin_zip if plugin_zip and plugin_zip.is_file() else None
        super().__init__(address, ReceiverHandler)


class ReceiverHandler(BaseHTTPRequestHandler):
    server: ClipReceiver

    def _json(self, status: int, value: dict):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"name": self.server.receiver_name, "version": 1})
        elif self.path == "/ClipExport.zip" and self.server.plugin_zip:
            path = self.server.plugin_zip
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    self.wfile.write(chunk)
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/pair":
            self._json(404, {"error": "Not found"})
            return
        ip = self.client_address[0]
        failed, first = self.server.failed_pairs.get(ip, (0, time.monotonic()))
        if time.monotonic() - first > 600:
            failed, first = 0, time.monotonic()
        if failed >= 5:
            self._json(429, {"error": "Too many attempts; restart receiver to pair"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > 1024:
                raise ValueError("Invalid body length")
            code = json.loads(self.rfile.read(size))["code"]
        except (ValueError, KeyError, TypeError):
            self._json(400, {"error": "Invalid pairing request"})
            return
        if (time.monotonic() > self.server.pair_deadline or
                not isinstance(code, str) or
                not hmac.compare_digest(code, self.server.pair_code)):
            self.server.failed_pairs[ip] = (failed + 1, first)
            self._json(403, {"error": "Incorrect or expired pairing code"})
            return
        self.server.failed_pairs.pop(ip, None)
        self._json(200, {"name": self.server.receiver_name, "token": self.server.token})

    def do_PUT(self):
        if not self.path.startswith("/upload/"):
            self._json(404, {"error": "Not found"})
            return
        auth = self.headers.get("Authorization", "")
        if not hmac.compare_digest(auth, "Bearer " + self.server.token):
            self._json(401, {"error": "Pair this computer first"})
            return
        name = unquote(urlsplit(self.path).path[len("/upload/"):])
        if (not name or name != Path(name).name or name in (".", "..") or
                "\\" in name or "\x00" in name or not name.lower().endswith(".mp4")):
            self._json(400, {"error": "Invalid filename"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        if size <= 0 or size > MAX_UPLOAD:
            self._json(413, {"error": "Missing or excessive Content-Length"})
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".deckyclip-", suffix=".part", dir=self.server.destination, delete=False) as out:
                temporary = Path(out.name)
                digest = hashlib.sha256()
                remaining = size
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ConnectionError("Upload ended early")
                    out.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
                out.flush()
                os.fsync(out.fileno())
            base = self.server.destination / name
            for suffix in range(1000):
                destination = base if suffix == 0 else base.with_name(f"{base.stem} ({suffix}){base.suffix}")
                try:
                    os.link(temporary, destination)
                    break
                except FileExistsError:
                    continue
            else:
                raise OSError("Too many files with the same name")
            self._json(201, {"name": destination.name, "size": size, "sha256": digest.hexdigest()})
        except (OSError, ConnectionError) as exc:
            self._json(500, {"error": str(exc)[:200]})
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def _local_address() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("1.1.1.1", 80))
            return sock.getsockname()[0]
    except OSError:
        return socket.gethostname() + ".local"


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive Steam Deck clips over the local network")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=57321)
    default_folder = "Movies" if sys.platform == "darwin" else "Videos"
    parser.add_argument("--dest", type=Path, default=Path.home() / default_folder / "Steam Deck Clips")
    parser.add_argument("--config", type=Path, default=Path.home() / ".config" / "decky-clip-receiver" / "config.json")
    parser.add_argument("--plugin-zip", type=Path, default=Path(__file__).resolve().parent.parent / "ClipExport-0.1.1.zip")
    args = parser.parse_args()
    server = ClipReceiver((args.host, args.port), args.dest, args.config, args.plugin_zip)
    print(f"Receiving clips in: {server.destination}")
    print(f"Decky receiver URL: http://{_local_address()}:{server.server_port}")
    print(f"Pairing code: {server.pair_code} (valid for 15 minutes)")
    if server.plugin_zip:
        print(f"Decky install URL: http://{_local_address()}:{server.server_port}/ClipExport.zip")
    print("Keep this window open while transferring. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
