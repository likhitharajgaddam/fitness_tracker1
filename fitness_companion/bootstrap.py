"""Self-healing pure-Python runtime bootstrap for Django dependencies.

Ensures Django and its pure-Python dependencies (asgiref, sqlparse) are
available on sys.path even in ephemeral containers where system-level pip
or global site-packages are absent after a cold start.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REQUIRED_MODULES = ("django", "asgiref", "sqlparse")

REQUIRED_PACKAGES = (
    ("Django", "5.2.8"),
    ("asgiref", "3.8.1"),
    ("sqlparse", "0.5.3"),
)

CACHE_DIR_NAME = "fittrack_pydeps_django52"
READY_MARKER = ".ready"


def _all_modules_available() -> bool:
    importlib.invalidate_caches()
    return all(importlib.util.find_spec(mod) is not None for mod in REQUIRED_MODULES)


def _prepend_to_path(target_dir: Path) -> None:
    target_str = str(target_dir)
    if target_str not in sys.path:
        sys.path.insert(0, target_str)
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    parts = [p for p in existing_pythonpath.split(os.pathsep) if p]
    if target_str not in parts:
        parts.insert(0, target_str)
        os.environ["PYTHONPATH"] = os.pathsep.join(parts)
    importlib.invalidate_caches()


def _fetch_wheel_url(package: str, version: str) -> tuple[str, str]:
    api_url = f"https://pypi.org/pypi/{package}/{version}/json"
    req = urllib.request.Request(
        api_url, headers={"User-Agent": "FitTrack-Bootstrap/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        metadata = json.loads(resp.read().decode("utf-8"))

    for entry in metadata.get("urls", []):
        if entry.get("packagetype") == "bdist_wheel" and entry.get("url"):
            sha256 = (entry.get("digests") or {}).get("sha256", "")
            return entry["url"], sha256

    raise RuntimeError(f"No pure-Python wheel found on PyPI for {package}=={version}")


def _extract_wheel(wheel_bytes: bytes, dest_dir: Path) -> None:
    dest_resolved = dest_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as zf:
        for member in zf.infolist():
            member_path = (dest_resolved / member.filename).resolve()
            if not str(member_path).startswith(str(dest_resolved) + os.sep):
                raise RuntimeError(f"Unsafe wheel path detected: {member.filename}")
            if member.is_dir():
                member_path.mkdir(parents=True, exist_ok=True)
            else:
                member_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member, "r") as src, open(member_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)


def _install_packages_into(cache_dir: Path) -> None:
    staging_dir = Path(tempfile.mkdtemp(prefix="fittrack_pydeps_stage_", dir=cache_dir.parent))
    try:
        for package, version in REQUIRED_PACKAGES:
            wheel_url, expected_sha256 = _fetch_wheel_url(package, version)
            req = urllib.request.Request(
                wheel_url, headers={"User-Agent": "FitTrack-Bootstrap/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                wheel_bytes = resp.read()

            if expected_sha256:
                actual_sha256 = hashlib.sha256(wheel_bytes).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise RuntimeError(
                        f"Checksum mismatch for {package}=={version}"
                    )

            _extract_wheel(wheel_bytes, staging_dir)

        (staging_dir / READY_MARKER).write_text("ok\n", encoding="utf-8")
        os.chmod(staging_dir, 0o755)
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
        os.replace(staging_dir, cache_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def _resolve_cache_dir() -> Path:
    base_tmp = Path(tempfile.gettempdir())
    shared = base_tmp / CACHE_DIR_NAME
    if (shared / READY_MARKER).is_file() and os.access(shared, os.R_OK | os.X_OK):
        return shared
    if not shared.exists() and os.access(base_tmp, os.W_OK):
        return shared
    if shared.exists() and os.access(shared, os.W_OK):
        return shared
    uid = getattr(os, "getuid", lambda: 0)()
    return base_tmp / f"{CACHE_DIR_NAME}_{uid}"


def ensure_django_dependencies() -> None:
    """Guarantee Django, asgiref, and sqlparse are importable."""
    if _all_modules_available():
        return

    cache_dir = _resolve_cache_dir()
    if (cache_dir / READY_MARKER).is_file():
        _prepend_to_path(cache_dir)
        if _all_modules_available():
            return

    lock_path = cache_dir.parent / f"{cache_dir.name}.lock"
    lock_file = open(lock_path, "w", encoding="utf-8")
    try:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass

        if (cache_dir / READY_MARKER).is_file():
            _prepend_to_path(cache_dir)
            if _all_modules_available():
                return

        sys.stderr.write(
            "[FitTrack] Installing Django runtime dependencies into cache...\n"
        )
        sys.stderr.flush()
        _install_packages_into(cache_dir)
        _prepend_to_path(cache_dir)
    finally:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        lock_file.close()
