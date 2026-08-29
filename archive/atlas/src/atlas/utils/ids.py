"""Anonymous identifier helpers.

Session IDs are random and carry no personal information. They exist so
logs and follow-up questions can be correlated within a single visit, and
nothing more.
"""

from __future__ import annotations

import uuid


def new_session_id() -> str:
    """Return a fresh anonymous session id, e.g. 'sess_3f9a...'."""
    return "sess_" + uuid.uuid4().hex


def new_event_id() -> str:
    """Return a fresh event id for a single log record."""
    return "evt_" + uuid.uuid4().hex
