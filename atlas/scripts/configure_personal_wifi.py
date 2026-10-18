"""Hidden-input personal Wi-Fi setup; no username, shell passwords or uploads.

prepare: create the camera header and a private transferable Jetson profile.
camera: create only the new primary camera header; old profiles stay untouched.
jetson: stage a root-only profile; activate only with explicit local-console flags.
"""

from __future__ import annotations

import argparse
import configparser
import getpass
import json
import os
import re
import stat
import subprocess
import sys
import uuid
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_NAME = "ATLAS-personal"
PROFILE_FILE = "atlas-personal.nmconnection"
NM_DIRECTORY = Path("/etc/NetworkManager/system-connections")


@dataclass(frozen=True)
class PersonalConfig:
    ssid: str = field(repr=False)
    password: str = field(repr=False)
    security: str = "auto"
    profile_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


def validate(config: PersonalConfig) -> None:
    if config.security not in {"auto", "wpa3"}:
        raise ValueError("Select auto or wpa3 personal security.")
    if not 1 <= len(config.ssid.encode("utf-8")) <= 32:
        raise ValueError("SSID must contain 1–32 UTF-8 bytes.")
    for value in (config.ssid, config.password):
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Control characters are not permitted.")
    if config.security == "wpa3":
        # Use the portable ESP32/NetworkManager passphrase range on both devices.
        valid_password = 8 <= len(config.password.encode("utf-8")) <= 63
    else:
        valid_password = (
            config.password.isascii() and 8 <= len(config.password) <= 63
        ) or bool(re.fullmatch(r"[0-9a-fA-F]{64}", config.password))
    if not valid_password:
        raise ValueError("Password is not valid for the selected personal mode.")
    uuid.UUID(config.profile_uuid)


def render_camera_header(config: PersonalConfig) -> str:
    validate(config)
    return (
        "#pragma once\n"
        "// PRIVATE: generated locally; never commit, print or share.\n"
        "constexpr bool WIFI_PERSONAL_CONFIGURED = true;\n"
        "constexpr bool WIFI_PERSONAL_WPA3_ONLY = "
        f"{str(config.security == 'wpa3').lower()};\n"
        "constexpr char WIFI_PERSONAL_SSID[] = "
        f"{json.dumps(config.ssid, ensure_ascii=False)};\n"
        "constexpr char WIFI_PERSONAL_PASSWORD[] = "
        f"{json.dumps(config.password, ensure_ascii=False)};\n"
    )


def keyfile_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\s")


def unescape_keyfile(value: str) -> str:
    # Only the two encodings emitted above are accepted; no newline injections.
    decoded = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            decoded.append(value[index])
            index += 1
            continue
        if index + 1 == len(value) or value[index + 1] not in {"\\", "s"}:
            raise ValueError("Unsupported private profile encoding.")
        decoded.append(" " if value[index + 1] == "s" else "\\")
        index += 2
    return "".join(decoded)


def render_jetson_profile(config: PersonalConfig) -> str:
    validate(config)
    ssid = ";".join(str(byte) for byte in config.ssid.encode("utf-8")) + ";"
    key_mgmt = "sae" if config.security == "wpa3" else "wpa-psk"
    pmf = 3 if config.security == "wpa3" else 2
    return (
        f"[connection]\nid={PROFILE_NAME}\nuuid={config.profile_uuid}\ntype=wifi\n"
        "autoconnect=false\nautoconnect-priority=200\nautoconnect-retries=1\n"
        "auth-retries=2\n\n"
        f"[wifi]\nmode=infrastructure\nssid={ssid}\n\n"
        f"[wifi-security]\nkey-mgmt={key_mgmt}\nproto=rsn;\npmf={pmf}\n"
        f"psk={keyfile_string(config.password)}\npsk-flags=0\n\n"
        "[ipv4]\nmethod=auto\n\n[ipv6]\nmethod=auto\n"
    )


def read_import_profile(path: Path) -> PersonalConfig:
    """Operator-authorized private import; never return its contents to output."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("Choose a regular small personal profile file.")
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(path.read_text(encoding="utf-8"))
    allowed = {
        "connection": {
            "id",
            "uuid",
            "type",
            "autoconnect",
            "autoconnect-priority",
            "autoconnect-retries",
            "auth-retries",
        },
        "wifi": {"mode", "ssid"},
        "wifi-security": {"key-mgmt", "proto", "pmf", "psk", "psk-flags"},
        "ipv4": {"method"},
        "ipv6": {"method"},
    }
    if parser.defaults() or set(parser.sections()) != set(allowed):
        raise ValueError("Not an ATLAS personal profile.")
    for section, fields in allowed.items():
        if set(parser[section]) != fields:
            raise ValueError("Unexpected private profile fields.")
    if parser["connection"]["id"] != PROFILE_NAME:
        raise ValueError("Unexpected connection ID.")
    raw_ssid = parser["wifi"]["ssid"]
    if not re.fullmatch(r"(?:\d{1,3};){1,32}", raw_ssid):
        raise ValueError("Invalid profile SSID encoding.")
    ssid = bytes(int(item) for item in raw_ssid.split(";")[:-1]).decode("utf-8")
    security = {"wpa-psk": "auto", "sae": "wpa3"}.get(
        parser["wifi-security"]["key-mgmt"]
    )
    config = PersonalConfig(
        ssid,
        unescape_keyfile(parser["wifi-security"]["psk"]),
        security or "invalid",
        parser["connection"]["uuid"],
    )
    validate(config)
    # Compare canonical values, not just section names: imported routes,
    # autoconnect, PMF or secret handling must not change our safe policy.
    canonical = configparser.ConfigParser(interpolation=None)
    canonical.read_string(render_jetson_profile(config))
    if any(dict(parser[section]) != dict(canonical[section]) for section in allowed):
        raise ValueError("Private profile does not match safe staging policy.")
    return config


def write_private_files(
    entries: dict[Path, str],
    *,
    replace_existing: bool = False,
) -> dict[Path, Path | None]:
    """Atomic per-file writes with batch rollback; never read old credentials."""
    for path in entries:
        if path.parent.is_symlink() or path.is_symlink():
            raise ValueError("Private destination must not be a symlink.")
        if path.exists() and (
            not replace_existing or not stat.S_ISREG(path.stat().st_mode)
        ):
            raise ValueError("Personal settings already exist; review --replace.")
    pending: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    installed: list[Path] = []
    try:
        for path, contents in entries.items():
            temporary = path.with_name(f".{path.name}.pending-{uuid.uuid4().hex}")
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            pending[path] = temporary
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())
        for path in entries:
            backup = None
            if path.exists():
                if path.is_symlink() or not replace_existing:
                    raise ValueError("Private destination changed during setup.")
                backup = path.with_name(f"{path.name}.backup-{uuid.uuid4().hex}")
                backups[path] = backup
                os.replace(path, backup)
            backups[path] = backup
            os.replace(pending[path], path)
            installed.append(path)
        return backups
    except BaseException:
        for path, backup in reversed(list(backups.items())):
            if backup is not None and backup.exists():
                os.replace(backup, path)
            elif path in installed:
                path.unlink(missing_ok=True)
        raise
    finally:
        for temporary in pending.values():
            temporary.unlink(missing_ok=True)


def nmcli(*arguments: str) -> str:
    return subprocess.run(
        ["nmcli", *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=55,
    ).stdout.strip()


def install_jetson(
    config: PersonalConfig,
    directory: Path,
    *,
    replace_existing: bool = False,
) -> str:
    names = nmcli("-g", "NAME", "connection", "show").splitlines()
    existing_uuids = nmcli("-g", "UUID", "connection", "show").splitlines()
    destination = directory / PROFILE_FILE
    existing = PROFILE_NAME in names
    if existing:
        if (
            not replace_existing
            or not destination.is_file()
            or destination.is_symlink()
        ):
            raise ValueError(
                "Personal profile exists; explicit owned replacement needed."
            )
        profile_uuid = nmcli(
            "-g", "connection.uuid", "connection", "show", "id", PROFILE_NAME
        )
        uuid.UUID(profile_uuid)
        config = replace(config, profile_uuid=profile_uuid)
    elif destination.exists():
        raise ValueError("Destination already exists; no unknown file replaced.")
    elif config.profile_uuid in existing_uuids:
        raise ValueError("Imported UUID belongs to another saved connection.")
    backups = write_private_files(
        {destination: render_jetson_profile(config)},
        replace_existing=replace_existing,
    )
    try:
        nmcli("connection", "load", str(destination))
    except BaseException:
        backup = backups[destination]
        if backup is not None:
            os.replace(backup, destination)
            nmcli("connection", "load", str(destination))
        else:
            # Delete only this invocation's newly generated profile, if a
            # partially successful NetworkManager load created it in memory.
            try:
                nmcli("connection", "delete", "uuid", config.profile_uuid)
            except subprocess.SubprocessError:
                pass
            destination.unlink(missing_ok=True)
        raise
    return config.profile_uuid


def hidden_input(prompt: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("prepare", "camera", "jetson"), required=True
    )
    parser.add_argument("--security", choices=("auto", "wpa3"), default="auto")
    parser.add_argument("--import-profile", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--local-console", action="store_true")
    args = parser.parse_args()
    if args.import_profile and args.target != "jetson":
        parser.error("Private profile import is Jetson-only.")
    if args.activate and (
        args.target != "jetson"
        or not args.local_console
        or os.environ.get("SSH_CONNECTION")
        or os.environ.get("SSH_TTY")
    ):
        parser.error("Activation requires --target jetson --local-console outside SSH.")
    if (not args.import_profile or args.activate) and not sys.stdin.isatty():
        parser.error("Use a real terminal with hidden input; do not pipe credentials.")
    if args.target == "jetson" and (os.name != "posix" or os.geteuid() != 0):
        parser.error("Jetson installation must run locally with sudo.")
    try:
        if args.import_profile:
            config = read_import_profile(args.import_profile)
        else:
            ssid = hidden_input("Wi-Fi SSID (hidden): ")
            password = hidden_input("Wi-Fi password (hidden): ")
            if password != hidden_input("Confirm Wi-Fi password (hidden): "):
                raise ValueError("Password confirmation differs.")
            config = PersonalConfig(ssid, password, args.security)
            validate(config)
        if args.target == "jetson":
            profile_uuid = install_jetson(
                config,
                NM_DIRECTORY,
                replace_existing=args.replace,
            )
            print("Saved root-only ATLAS-personal; existing networks unchanged.")
            if args.activate:
                nmcli("--wait", "40", "connection", "up", "uuid", profile_uuid)
                nmcli(
                    "connection",
                    "modify",
                    "uuid",
                    profile_uuid,
                    "connection.autoconnect",
                    "yes",
                )
                print("Personal Wi-Fi activated and enabled for future auto-connect.")
                print(
                    "Verify the actual IP and camera traffic; old addresses may change."
                )
            else:
                print("Auto-connect is OFF. No active link was switched.")
        else:
            entries = {
                ROOT
                / "firmware/xiao_camera/wifi_personal_secrets.h": render_camera_header(
                    config
                ),
            }
            if args.target == "prepare":
                private = ROOT / ".private-network"
                if private.is_symlink():
                    raise ValueError("Private staging directory must not be a symlink.")
                private.mkdir(mode=0o700, exist_ok=True)
                entries[private / PROFILE_FILE] = render_jetson_profile(config)
            write_private_files(entries, replace_existing=args.replace)
            print(
                "Saved private personal settings. Old school/hotspot headers unchanged."
            )
            if args.target == "prepare":
                print("Jetson profile: .private-network/atlas-personal.nmconnection")
                print(
                    "Transfer privately, then import locally with sudo on the Jetson."
                )
            print(
                "Not flashed or connected. Run the reviewed camera upload separately."
            )
            print("Private files/builds can be synced by OneDrive; never share them.")
        return 0
    except (
        ValueError,
        OSError,
        EOFError,
        getpass.GetPassWarning,
        configparser.Error,
        subprocess.SubprocessError,
    ):
        # No exception/provider output: it may contain credentials or SSIDs.
        print("Setup failed; check input, permissions, personal settings or network.")
        print("No other saved network was changed. Check the local-console state.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
