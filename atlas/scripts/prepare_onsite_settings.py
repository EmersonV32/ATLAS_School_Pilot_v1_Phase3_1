"""Stage only the approved non-secret onsite migration; dry-run by default.

Never imports the application loader or dotenv. No devices, network, installed
units, model files, credentials or packages are inspected or changed.
"""

from __future__ import annotations

import argparse
import copy
import ipaddress
import os
import re
import stat
import tempfile
import uuid
from pathlib import Path

import yaml

SPEECH_PATCH = {
    "listen_duration_s": 8.0,
    "max_utterance_s": 45.0,
    "silero_min_silence_ms": 2000,
    "silero_hesitation_silence_ms": 4000,
}
BACKUP_FOLDER = ".atlas-onsite-settings-backups"


class PreparationError(RuntimeError):
    """Safe operator-facing failure; never include existing configuration."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not silently accept contradictory duplicate configuration keys."""


def _unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise PreparationError("Configuration keys must be unique strings.")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def camera_endpoints(host: str) -> dict[str, str]:
    """Accept an IP/DNS hostname only, never a URL, port, path or shell text."""
    if not host or host != host.strip() or len(host) > 253:
        raise PreparationError("Camera host must be an IP address or DNS hostname.")
    candidate = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        labels = candidate.split(".")
        if (
            candidate.casefold() == "localhost"
            or all(label.isdigit() for label in labels)
            or any(
                not re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label
                )
                for label in labels
            )
        ):
            raise PreparationError(
                "Camera host must be an IP address or DNS hostname."
            ) from None
        authority = candidate
    else:
        if address.is_unspecified or address.is_loopback or address.is_multicast:
            raise PreparationError("Camera host must identify the camera on the LAN.")
        authority = f"[{address}]" if address.version == 6 else str(address)
    return {
        "camera_source": f"http://{authority}:81/stream",
        "camera_control_url": f"http://{authority}",
    }


def _safe_path(path: Path) -> None:
    if path.is_symlink() or path.resolve() != path.absolute():
        raise PreparationError(
            "Symlinks and redirected configuration paths are refused."
        )


def _validate_root(root: Path) -> Path:
    if not root.is_absolute() or ".." in root.parts:
        raise PreparationError("--root must be an explicit absolute application path.")
    _safe_path(root)
    if (
        len(root.parts) < 3
        or root.name.casefold() in {"home", "tmp", "usr", "var", "opt", "root", "etc"}
        or not (root / "src/atlas").is_dir()
        or not (root / "config/settings.yaml").is_file()
    ):
        raise PreparationError("Root is not a supported existing ATLAS application.")
    for path in (root / "src/atlas", root / "config", root / BACKUP_FOLDER):
        _safe_path(path)
    return root


def _load_mapping(contents: bytes | None) -> dict:
    if contents is None:
        return {}
    try:
        loaded = yaml.load(contents.decode("utf-8-sig"), Loader=UniqueKeyLoader)
    except (UnicodeError, yaml.YAMLError, ValueError, TypeError) as exc:
        raise PreparationError("Configuration is not valid unambiguous YAML.") from exc
    if not isinstance(loaded, dict):
        raise PreparationError("Each configuration file must contain a YAML mapping.")
    return loaded


def _patched(document: dict, camera: dict[str, str] | None) -> dict:
    result = copy.deepcopy(document)
    patches = {"speech": SPEECH_PATCH, "camera_pan": {"enabled": False}}
    if camera:
        patches["hardware"] = camera
    for section, patch in patches.items():
        if section in result and not isinstance(result[section], dict):
            raise PreparationError("A migration section is not a YAML mapping.")
        result.setdefault(section, {}).update(patch)
    return result


def _atomic_write(path: Path, contents: bytes, mode: int) -> None:
    _safe_path(path)
    descriptor, name = tempfile.mkstemp(prefix=".atlas-settings-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(
    root: Path, *, camera_host: str | None = None, apply: bool = False
) -> Path | None:
    root = _validate_root(root)
    camera = camera_endpoints(camera_host) if camera_host is not None else None
    paths = (root / "config/settings.yaml", root / "config/dashboard_overrides.yaml")
    originals: dict[Path, bytes | None] = {}
    documents = {}
    for path in paths:
        _safe_path(path)
        if path.exists() and not path.is_file():
            raise PreparationError("Configuration targets must be regular files.")
        originals[path] = path.read_bytes() if path.exists() else None
        documents[path] = _load_mapping(originals[path])
    dashboard = documents[paths[0]].get("dashboard", {})
    if not isinstance(dashboard, dict):
        raise PreparationError("Dashboard configuration must be a mapping.")
    configured = dashboard.get("config_override_path")
    if configured is not None:
        if not isinstance(configured, str):
            raise PreparationError(
                "Custom dashboard override path needs separate review."
            )
        override = Path(configured)
        if (root / override).resolve() != paths[1].resolve():
            raise PreparationError(
                "Custom dashboard override path needs separate review."
            )
    updated = {
        path: yaml.safe_dump(_patched(document, camera), sort_keys=False).encode(
            "utf-8"
        )
        for path, document in documents.items()
    }
    if not apply:
        return None
    backup = root / BACKUP_FOLDER / uuid.uuid4().hex
    backup.mkdir(parents=True, mode=0o700)
    for path, contents in originals.items():
        if contents is not None:
            destination = backup / path.name
            with destination.open("xb") as handle:
                handle.write(contents)
            destination.chmod(0o600)
    modes = {
        path: stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        for path in paths
    }
    written = []
    try:
        for path in paths:
            _safe_path(path)
            current = path.read_bytes() if path.exists() else None
            if current != originals[path]:
                raise PreparationError(
                    "Configuration changed during preparation; retry."
                )
            written.append(path)
            _atomic_write(path, updated[path], modes[path])
    except Exception as exc:
        rollback_failed = False
        for path in reversed(written):
            try:
                _safe_path(path)
                current = path.read_bytes() if path.exists() else None
                if current == originals[path]:
                    continue
                if originals[path] is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, originals[path], modes[path])
            except Exception:
                rollback_failed = True
        if rollback_failed:
            raise PreparationError(
                "ROLLBACK INCOMPLETE. Keep ATLAS stopped; "
                "restore the saved YAML backups."
            ) from exc
        raise PreparationError(
            "Settings update failed; prior files were restored."
        ) from exc
    return backup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--camera-host", help="Verified LAN IP or mDNS hostname only")
    parser.add_argument(
        "--apply", action="store_true", help="Authorize the YAML migration"
    )
    args = parser.parse_args(argv)
    try:
        backup = prepare(args.root, camera_host=args.camera_host, apply=args.apply)
        print("Approved patch in settings.yaml and dashboard_overrides.yaml:")
        for key, value in SPEECH_PATCH.items():
            print(f"  speech.{key} = {value}")
        print(
            "  camera_pan.enabled = false (mechanical commissioning remains separate)"
        )
        if args.camera_host is not None:
            for key, value in camera_endpoints(args.camera_host).items():
                print(f"  hardware.{key} = {value}")
        print(
            "Applied with YAML backups."
            if backup
            else "Dry-run only; no files changed."
        )
        if backup:
            print(f"Backup: {BACKUP_FOLDER}/{backup.name}")
        print("No service was restarted. Environment overrides can still win.")
        print(
            "After approved restart, confirm active settings AND "
            "the actual camera source."
        )
        print(
            "HTTP 200 alone cannot certify physical readiness; "
            "run live acceptance tests."
        )
        return 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, PreparationError) else type(exc).__name__
        print(f"Preparation refused: {message}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
