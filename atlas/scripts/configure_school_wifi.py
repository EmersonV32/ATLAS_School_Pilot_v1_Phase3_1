"""Operator-run offline PEAP setup; never connect, flash, or print credentials."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import ssl
import subprocess
import sys
import uuid
import warnings
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_NAME = "ATLAS-school"
RISK_CONFIRMATION = "I ACCEPT THE RISK"


@dataclass(frozen=True)
class SchoolConfig:
    ssid: str
    username: str = field(repr=False)
    password: str = field(repr=False)
    identity: str = field(repr=False)
    ca_pem: str = ""
    server_name: str = ""
    allow_unverified: bool = False
    ca_path: str = ""


def validate(config: SchoolConfig) -> None:
    for label, value, limit in (
        ("SSID", config.ssid, 32),
        ("username", config.username, 127),
        ("password", config.password, 64),
        ("identity", config.identity, 127),
    ):
        if not value or len(value.encode("utf-8")) > limit:
            raise ValueError(f"Invalid {label} length (maximum {limit} UTF-8 bytes).")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError(f"Control characters are not allowed in {label}.")
    has_ca = bool(config.ca_pem)
    has_server = bool(config.server_name)
    if has_ca != has_server:
        raise ValueError("Provide both the trusted CA and expected server name.")
    if has_ca:
        if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", config.server_name):
            raise ValueError("Invalid expected authentication-server name.")
        if "PRIVATE KEY" in config.ca_pem:
            raise ValueError(
                "A public CA certificate is required, never a private key."
            )
        ssl.PEM_cert_to_DER_cert(config.ca_pem)
        if any(ord(char) < 32 for char in config.ca_path):
            raise ValueError("Control characters are not allowed in the CA path.")
    elif not config.allow_unverified:
        raise ValueError("Server verification is required unless explicitly opted out.")


def render_camera_header(config: SchoolConfig) -> str:
    validate(config)
    fields = {
        "SSID": config.ssid,
        "IDENTITY": config.identity,
        "USERNAME": config.username,
        "PASSWORD": config.password,
        "CA_PEM": config.ca_pem,
        "SERVER_NAME": config.server_name,
    }
    lines = [
        "#pragma once",
        "// PRIVATE: generated locally; never commit, print or share this file.",
        "constexpr bool WIFI_SCHOOL_CONFIGURED = true;",
        "constexpr bool WIFI_SCHOOL_ALLOW_UNVERIFIED_SERVER = "
        f"{str(config.allow_unverified).lower()};",
    ]
    lines.extend(
        f"constexpr char WIFI_SCHOOL_{key}[] = {json.dumps(value, ensure_ascii=False)};"
        for key, value in fields.items()
    )
    return "\n".join(lines) + "\n"


def keyfile_string(value: str) -> str:
    # GLib keyfile escaping, not shell escaping. Preserve spaces/backslashes.
    return value.replace("\\", "\\\\").replace(" ", "\\s")


def render_jetson_profile(config: SchoolConfig) -> str:
    validate(config)
    if config.ca_pem and not config.ca_path.startswith("/"):
        raise ValueError("The Jetson requires the absolute CA certificate path.")
    # Serialize SSID bytes explicitly so semicolons/non-ASCII are unambiguous.
    ssid_bytes = ";".join(str(byte) for byte in config.ssid.encode("utf-8")) + ";"
    lines = [
        "[connection]",
        f"id={PROFILE_NAME}",
        f"uuid={uuid.uuid4()}",
        "type=wifi",
        "autoconnect=false",
        "autoconnect-priority=100",
        "autoconnect-retries=1",
        "auth-retries=2",
        "",
        "[wifi]",
        "mode=infrastructure",
        f"ssid={ssid_bytes}",
        "",
        "[wifi-security]",
        "key-mgmt=wpa-eap",
        "",
        "[802-1x]",
        "eap=peap;",
        "phase2-auth=mschapv2",
        f"identity={keyfile_string(config.username)}",
        f"anonymous-identity={keyfile_string(config.identity)}",
        f"password={keyfile_string(config.password)}",
        "password-flags=0",
        "system-ca-certs=false",
    ]
    if config.ca_pem:
        lines += [
            f"ca-cert={keyfile_string(config.ca_path)}",
            f"domain-match={config.server_name}",
        ]
    lines += ["", "[ipv4]", "method=auto", "", "[ipv6]", "method=auto", ""]
    return "\n".join(lines)


def write_private_new(path: Path, contents: str) -> None:
    # Never overwrite a profile/header, follow a destination symlink, or read it.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def hidden_input(prompt: str) -> str:
    # Refuse getpass's echoing fallback if the terminal cannot hide input.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def install_jetson(config: SchoolConfig, directory: Path) -> Path:
    names = subprocess.run(
        ["nmcli", "-g", "NAME", "connection", "show"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if PROFILE_NAME in names:
        raise ValueError("ATLAS-school already exists; no existing profile changed.")
    path = directory / "atlas-school.nmconnection"
    write_private_new(path, render_jetson_profile(config))
    try:
        subprocess.run(
            ["nmcli", "connection", "load", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except BaseException:
        # This invocation created this exact file exclusively. No older file lost.
        path.unlink(missing_ok=True)
        raise
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("camera", "jetson"), required=True)
    parser.add_argument("--ssid", default="CBourget")
    parser.add_argument("--ca-cert", type=Path)
    parser.add_argument("--server-name", default="")
    parser.add_argument("--allow-unverified-server", action="store_true")
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("Use an interactive terminal; do not pipe or log credentials.")
    if args.target == "jetson" and (os.name != "posix" or os.geteuid() != 0):
        parser.error("Run Jetson setup on the Jetson with sudo; no files changed.")
    if bool(args.ca_cert) != bool(args.server_name):
        parser.error("Provide --ca-cert and --server-name together.")
    if not args.ca_cert:
        if not args.allow_unverified_server:
            parser.error("Supply server trust settings or explicitly opt into risk.")
        print("WARNING: an unverified school access point can steal your password.")
        print("This PEAP/MSCHAPv2 assumption has NOT been tested at the school.")
        if input(f"Type {RISK_CONFIRMATION} to continue: ") != RISK_CONFIRMATION:
            print("Cancelled. No files or network settings changed.")
            return 1
    try:
        ca_path = str(args.ca_cert.resolve()) if args.ca_cert else ""
        ca_pem = args.ca_cert.read_text(encoding="utf-8") if args.ca_cert else ""
        username = hidden_input("School username (hidden): ")
        password = hidden_input("School password (hidden): ")
        config = SchoolConfig(
            args.ssid,
            username,
            password,
            username,
            ca_pem,
            args.server_name,
            args.allow_unverified_server and not ca_pem,
            ca_path,
        )
        validate(config)
        if args.target == "camera":
            destination = ROOT / "firmware/xiao_camera/wifi_school_secrets.h"
            write_private_new(destination, render_camera_header(config))
            print("Saved the ignored school header. Existing hotspot unchanged.")
            print("Not flashed. Build/upload separately after reviewing the risk.")
        else:
            install_jetson(config, Path("/etc/NetworkManager/system-connections"))
            print("Saved ATLAS-school with autoconnect OFF. Current link unchanged.")
            print("School priority 100; one automatic activation before fallback.")
            print("Enable school/hotspot policy locally using SCHOOL_WIFI_SETUP.md.")
    except (
        ValueError,
        OSError,
        EOFError,
        getpass.GetPassWarning,
        subprocess.SubprocessError,
    ):
        # Never emit exception text that might contain a credential or PEM value.
        print("Setup failed: check input/trust settings or an existing destination.")
        print("No existing profile/header was overwritten; no connection activated.")
        return 1
    print("School authentication and camera-to-Jetson traffic remain UNTESTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
