"""Persistent app configuration (vault path, port) stored under ~/.obsidiansync/config.json."""
import json
import socket
from pathlib import Path

CONFIG_DIR = Path.home() / ".obsidiansync"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "vault_path": "",
    "port": 8765,
    "device_name": socket.gethostname(),
}


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save(DEFAULTS)
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_local_ip() -> str:
    """Best-effort LAN IP (the address other devices on the same Wi-Fi would use)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
