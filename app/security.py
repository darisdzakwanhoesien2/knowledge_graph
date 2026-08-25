"""Optional curator gate for write endpoints.

Upload/publish endpoints are the first write path in an otherwise read-only
API, so they accept a shared token via KG_CURATOR_TOKEN (see
docs/UPLOAD_SYSTEM_PLAN.md §3): when the variable is unset the endpoint stays
open for the local-first MVP; when set, requests must carry a matching
X-Curator-Token header.
"""
import os

from fastapi import Header, HTTPException


def require_curator(x_curator_token: str = Header(default="")):
    expected = os.environ.get("KG_CURATOR_TOKEN")
    if not expected:
        return
    if x_curator_token != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Curator-Token header")
