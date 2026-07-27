"""
Reusable wait helpers for Playwright tests.

Keep test files clean by extracting common wait patterns here.
"""

import allure
from playwright.sync_api import Page


@allure.step("Wait for element '{selector}' to become {state}")
def wait_for_element(page: Page, selector: str, state: str = "visible", timeout: int = 10000):
    """Wait for an element to reach the given *state*."""
    page.locator(selector).first.wait_for(state=state, timeout=timeout)


@allure.step("Wait for text '{text}' to appear on page")
def wait_for_text(page: Page, text: str, timeout: int = 10000):
    """Wait until the given *text* is visible anywhere on the page."""
    page.get_by_text(text).first.wait_for(state="visible", timeout=timeout)


@allure.step("Wait for network idle")
def wait_for_network_idle(page: Page):
    """Block until there are no pending network requests."""
    page.wait_for_load_state("networkidle")


@allure.step("Wait for localStorage key '{key}' to be populated")
def wait_for_local_storage(page: Page, key: str, timeout: int = 15000):
    """Block until the given key exists in window.localStorage."""
    page.wait_for_function(
        f"window.localStorage.getItem('{key}') != null",
        timeout=timeout,
    )
