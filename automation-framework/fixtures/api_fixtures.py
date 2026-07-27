"""
API request context fixture.

Provides a session-scoped, pre-authenticated Playwright APIRequestContext
for all API tests.
"""

import pytest
from playwright.sync_api import Playwright
from utils.auth_helpers import extract_auth_token


@pytest.fixture(scope="session")
def api_context(playwright: Playwright, config, global_auth_state):
    """
    Creates a Playwright API request context pre-configured with the
    auth token extracted from the global storage state.

    Session-scoped for performance — all API tests share one context.
    """
    token = extract_auth_token(str(global_auth_state))

    request_context = playwright.request.new_context(
        base_url=config["api_base_url"],
        extra_http_headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    yield request_context
    request_context.dispose()
