"""Local admin-token guard for dangerous dashboard endpoints.

The token is read at request time from the environment variable named by
settings.dashboard.admin_token_env (default ATLAS_ADMIN_TOKEN). It is never
stored in code, YAML, or logs. If the env var is not set, protected
endpoints are disabled entirely (secure default), returning 503.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException

ADMIN_HEADER = "X-Atlas-Admin-Token"


def make_admin_guard(admin_token_env: str):
    """Return a FastAPI dependency enforcing the admin token."""

    def require_admin(
        x_atlas_admin_token: str | None = Header(default=None, alias=ADMIN_HEADER),
    ) -> None:
        expected = os.getenv(admin_token_env, "")
        if not expected:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Admin endpoints disabled: set the {admin_token_env} "
                    "environment variable to enable them."
                ),
            )
        if not x_atlas_admin_token or not hmac.compare_digest(
            x_atlas_admin_token, expected
        ):
            raise HTTPException(status_code=401, detail="Invalid admin token.")

    return require_admin
