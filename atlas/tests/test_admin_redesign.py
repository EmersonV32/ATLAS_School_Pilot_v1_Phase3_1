"""Static contracts for the private dashboard; live layouts use browser QA."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/atlas/dashboard"
HTML = (ROOT / "templates/admin.html").read_text(encoding="utf-8")
JS = (ROOT / "static/admin.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/style.css").read_text(encoding="utf-8")


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.panels = {}
        self.assets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if "data-admin-views" in values:
            self.panels[values["aria-labelledby"]] = values["data-admin-views"].split()
        if tag in {"script", "link"}:
            self.assets.append(values.get("src", values.get("href", "")))


def test_every_literal_script_target_exists_once():
    elements = Elements()
    elements.feed(HTML)
    assert len(elements.ids) == len(set(elements.ids))
    assert set(re.findall(r'\$\("([\w-]+)"\)', JS)) <= set(elements.ids)


def test_overview_keeps_setup_and_logs_in_dedicated_views():
    elements = Elements()
    elements.feed(HTML)
    assert elements.panels["settings-title"] == ["settings"]
    assert elements.panels["logs-title"] == ["logs"]
    assert "main" in elements.panels["camera-title"]
    assert "main" in elements.panels["operations-title"]


def test_persistent_faults_and_camera_empty_states_have_accessible_targets():
    elements = Elements()
    elements.feed(HTML)
    targets = {
        "issue-title", "issue-list", "camera-empty", "arducam-empty", "last-sync",
    }
    assert targets <= set(elements.ids)
    assert 'aria-live="polite"' in HTML
    assert 'href="#dashboard-heading"' in HTML
    assert "focus-visible" in CSS
    assert "prefers-reduced-motion" in CSS


def test_no_remote_assets_framework_or_private_browser_profile():
    elements = Elements()
    elements.feed(HTML)
    assert all(asset.startswith("/static/") for asset in elements.assets)
    assert "@import" not in CSS
    assert "localStorage" not in JS
    assert "status.last_answer.answer :" not in JS
    visitor_html = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    assert "issue-board" not in visitor_html
    assert "admin.js" not in visitor_html
    assert "/static/style.css" not in visitor_html


def test_original_emergency_stop_and_routes_still_exist():
    for route in (
        "/hardware/emergency-stop", "/hardware/clear-emergency-stop",
        "/api/admin/demo/start", "/session/manual-artwork", "/session/capture",
        "/content/ingest", "/eval/rag", "/admin/config",
    ):
        assert route in JS
    assert 'catch((error) => notice(error.message, true))' in JS
