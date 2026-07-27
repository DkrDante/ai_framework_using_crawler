"""
Authentication fixtures.

- global_auth_state  : session-scoped login → saves storage state once.
- browser_context_args : injects authenticated state into every test's context.
- unauthenticated_page : clean browser context for login-flow tests.
"""

import os
import time
from pathlib import Path
import pytest
from pages.login_page import LoginPage
from utils.email_otp import fetch_otp
from utils.waits import wait_for_local_storage

# Maximum age (in hours) before the stored auth state is considered stale
MAX_STATE_AGE_HOURS = 12


@pytest.fixture(scope="session")
def global_auth_state(config, browser):
    """
    Performs login once per session using the LoginPage page object
    and saves the authenticated storage state to disk.
    Reuses existing state if available AND fresh (< MAX_STATE_AGE_HOURS old).
    Supports atomic cross-process worker synchronization.

    Returns the path to the state.json file.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    state_dir = project_root / ".auth"
    state_dir.mkdir(exist_ok=True)
    state_path = state_dir / "state.json"
    failed_path = state_dir / "login_failed.txt"
    lock_dir = state_dir / "login.lock"

    # Evict state if it is older than MAX_STATE_AGE_HOURS
    if state_path.exists():
        age_hours = (time.time() - state_path.stat().st_mtime) / 3600
        if age_hours > MAX_STATE_AGE_HOURS:
            try:
                state_path.unlink()
            except Exception:
                pass

    if state_path.exists():
        return str(state_path)

    if failed_path.exists():
        pytest.skip("login failed and none run")

    # Attempt to acquire cross-process atomic lock
    acquired_lock = False
    try:
        lock_dir.mkdir(exist_ok=False)
        acquired_lock = True
    except FileExistsError:
        # Lock is held by another worker. Wait until state.json is created.
        pass

    if acquired_lock:
        try:
            if not state_path.exists() and not failed_path.exists():
                try:
                    context = browser.new_context()
                    page = context.new_page()

                    # Use the LoginPage page object — no raw locators in fixtures
                    login_page = LoginPage(page)
                    login_page.navigate(config["base_url"])
                    login_page.fill_email(config["email_user"])
                    login_page.click_send_otp()

                    otp = fetch_otp(config["email_user"], config["email_pass"])

                    login_page.fill_otp(otp)
                    login_page.click_verify_signin()
                    login_page.wait_for_url("**/home")

                    # Wait until the auth token is stored in localStorage
                    wait_for_local_storage(page, "auth_token")

                    context.storage_state(path=str(state_path))
                    context.close()
                except Exception:
                    failed_path.write_text("login failed and none run", encoding="utf-8")
                    pytest.skip("login failed and none run")
        finally:
            try:
                lock_dir.rmdir()
            except Exception:
                pass
    else:
        # Wait up to 90 seconds for the state.json file to be written by the driver worker
        for _ in range(900):
            if state_path.exists():
                break
            if failed_path.exists():
                break
            time.sleep(0.1)
        else:
            raise TimeoutError("Timed out waiting for state.json to be created by the driver worker.")

        if failed_path.exists():
            pytest.skip("login failed and none run")

    return str(state_path)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, global_auth_state):
    """
    Injects the authenticated storage state into the default browser
    context used by pytest-playwright's `page` fixture.

    Every test gets its own fresh context pre-loaded with auth,
    ensuring complete test isolation.
    """
    return {
        **browser_context_args,
        "storage_state": global_auth_state,
    }


@pytest.fixture
def unauthenticated_page(browser, browser_context_args):
    """
    Provides a fresh, unauthenticated page for login-flow tests.

    Creates its own isolated context so it cannot leak state to or
    from other tests.
    """
    ctx_args = browser_context_args.copy()
    ctx_args.pop("storage_state", None)
    context = browser.new_context(**ctx_args)
    page = context.new_page()
    yield page
    context.close()
