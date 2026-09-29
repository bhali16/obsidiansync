"""Builds the file manifest for a vault directory (path, hash, size, mtime)."""
import hashlib
from pathlib import Path

IGNORED_DIR_NAMES = {".git", ".trash", ".DS_Store"}
IGNORED_FILE_NAMES = {".DS_Store"}


def _should_skip_dir(name: str) -> bool:
    return name in IGNORED_DIR_NAMES


def _should_skip_file(name: str) -> bool:
    return name in IGNORED_FILE_NAMES


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(vault_path: str) -> list[dict]:
    root = Path(vault_path)
    if not root.is_dir():
        return []

    entries = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(_should_skip_dir(part) for part in path.relative_to(root).parts[:-1]):
            continue
        if _should_skip_file(path.name):
            continue
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        entries.append(
            {
                "path": rel,
                "hash": _hash_file(path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        )
    return entries


def resolve_file(vault_path: str, rel_path: str) -> Path | None:
    """Safely resolve a manifest-relative path within the vault, rejecting traversal."""
    root = Path(vault_path).resolve()
    candidate = (root / rel_path).resolve()
    if root not in candidate.parents and candidate != root:
        return None
    if not str(candidate).startswith(str(root)):
        return None
    if not candidate.is_file():
        return None
    return candidate
