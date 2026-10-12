"""Read-only direct-PWM preflight. Does not load settings/.env or move a motor.

Run with the SAME unprivileged user as atlas.service. Discovery is not proof
of waveform routing, signal drive, safe power, or calibrated physical travel.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def inspect_pwm(root: Path = Path("/sys/class/pwm")) -> dict:
    from atlas.hardware.camera_pan_driver import JETSON_HEADER_PWM

    results = []
    for pin, identity in JETSON_HEADER_PWM.items():
        matches = [
            chip
            for chip in root.glob("pwmchip*")
            if (chip / "device").resolve().name == identity
        ]
        result = {
            "physical_header_pin": pin,
            "controller": identity,
            "found": len(matches) == 1,
            "physical_validation": "required",
        }
        if len(matches) == 1:
            chip = matches[0]
            try:
                result.update(
                    chip=str(chip),
                    channel_count=int((chip / "npwm").read_text(encoding="ascii")),
                    already_exported=(chip / "pwm0").exists(),
                    export_writable=os.access(chip / "export", os.W_OK),
                    unexport_writable=os.access(chip / "unexport", os.W_OK),
                )
            except (OSError, ValueError):
                result["inspection_error"] = "Cannot read kernel PWM metadata"
        results.append(result)
    return {
        "read_only": True,
        "candidates": results,
        "notice": "No motor test performed. Verify pinmux, waveform, power and travel.",
    }


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    print(json.dumps(inspect_pwm(), indent=2))
