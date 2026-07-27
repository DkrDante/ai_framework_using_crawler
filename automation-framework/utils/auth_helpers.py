"""
Utility helpers for extracting authentication tokens from Playwright storage state.
"""

import json


def extract_auth_token(state_path: str) -> str:
    """
    Read a Playwright storage-state JSON file and return the auth_token
    from localStorage.

    Raises ValueError if the token is not found.
    """
    with open(state_path, "r") as f:
        state = json.load(f)

    for origin in state.get("origins", []):
        for ls_item in origin.get("localStorage", []):
            if ls_item["name"] == "auth_token":
                return ls_item["value"]

    raise ValueError("auth_token not found in storage state.")
