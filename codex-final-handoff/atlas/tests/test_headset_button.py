"""Tests for the dependency-free Shokz multifunction-button listener."""

from __future__ import annotations

import struct

from atlas.app.headset_button import (
    ClickAccumulator,
    decode_input_events,
    find_consumer_control_device,
)


def test_shokz_consumer_control_device_is_discovered(tmp_path):
    devices = tmp_path / "devices"
    devices.write_text(
        'N: Name="Shokz Loop120 by Shokz Consumer Control"\n'
        "H: Handlers=kbd event4\n\n"
        'N: Name="Other keyboard"\nH: Handlers=kbd event9\n',
        encoding="utf-8",
    )
    assert find_consumer_control_device("Shokz", devices) == "/dev/input/event4"


def test_linux_input_events_are_decoded():
    record = struct.pack("@llHHI", 1, 2, 1, 164, 1)
    assert decode_input_events(record) == [(1, 164, 1)]


def test_button_clicks_are_grouped_into_single_double_and_triple():
    single = ClickAccumulator(0.55)
    assert single.press(1.0) is None
    assert single.flush(1.56) == 1

    double = ClickAccumulator(0.55)
    assert double.press(2.0) is None
    assert double.press(2.2) is None
    assert double.flush(2.76) == 2

    triple = ClickAccumulator(0.55)
    assert triple.press(3.0) is None
    assert triple.press(3.2) is None
    assert triple.press(3.4) is None
    assert triple.flush(3.96) == 3
