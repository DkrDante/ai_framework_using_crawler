"""
BasePage — foundation for all Page Object classes.

Contains only locator helpers and reusable page-level actions.
No assertions should ever live here.
"""

import allure
from playwright.sync_api import Page, Locator, expect


class BasePage:
    """Base class that every page object inherits from."""

    def __init__(self, page: Page):
        self.page = page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @allure.step("Navigate to {url}")
    def navigate(self, url: str, timeout: int = 60000):
        """Navigate to the given URL.
        
        Args:
            url: The URL to navigate to.
            timeout: Navigation timeout in milliseconds (default 60s to handle
                     slow server responses under parallel test load).
        """
        self.page.goto(url, timeout=timeout)

    @allure.step("Wait for URL pattern: {url_pattern}")
    def wait_for_url(self, url_pattern: str, timeout: int = 60000):
        """Block until the current URL matches *url_pattern*.

        Uses wait_until='commit' because SatoriXR is a React SPA —
        client-side routing changes the URL without a full page load.
        """
        self.page.wait_for_url(url_pattern, timeout=timeout, wait_until="commit")

    @allure.step("Reload the page")
    def reload(self):
        """Reload the current page."""
        self.page.reload()

    # ------------------------------------------------------------------
    # Element locators
    # ------------------------------------------------------------------

    @allure.step("Get element by role '{role}' and name '{name}'")
    def get_by_role(self, role: str, name: str = None) -> Locator:
        """Locate an element by its ARIA role and optional accessible name."""
        if name:
            return self.page.get_by_role(role, name=name)
        return self.page.get_by_role(role)

    @allure.step("Get element by text '{text}'")
    def get_by_text(self, text: str, exact: bool = False) -> Locator:
        """Locate an element by its visible text content."""
        return self.page.get_by_text(text, exact=exact)

    @allure.step("Get element by test id '{test_id}'")
    def get_by_test_id(self, test_id: str) -> Locator:
        """Locate an element by its data-testid attribute."""
        return self.page.get_by_test_id(test_id)

    @allure.step("Get element by placeholder '{placeholder}'")
    def get_by_placeholder(self, placeholder: str) -> Locator:
        """Locate an input by its placeholder text."""
        return self.page.get_by_placeholder(placeholder)

    @allure.step("Get element by label '{label}'")
    def get_by_label(self, label: str) -> Locator:
        """Locate a form element by its associated label."""
        return self.page.get_by_label(label)

    @allure.step("Get locator using selector '{selector}'")
    def locator(self, selector: str) -> Locator:
        """Return a Playwright Locator for a raw CSS / Playwright selector."""
        return self.page.locator(selector)

    # ------------------------------------------------------------------
    # Common actions
    # ------------------------------------------------------------------

    @allure.step("Click element: {selector}")
    def click(self, selector: str, timeout: int = 10000):
        """Click the first element matching *selector*."""
        self.page.locator(selector).first.click(timeout=timeout)

    @allure.step("Fill '{selector}' with value")
    def fill(self, selector: str, value: str, timeout: int = 10000):
        """Clear and type *value* into the element matching *selector*."""
        self.page.locator(selector).first.fill(value, timeout=timeout)

    @allure.step("Get inner text of '{selector}'")
    def get_text(self, selector: str) -> str:
        """Return the inner text of the first matching element."""
        return self.page.locator(selector).first.inner_text().strip()

    @allure.step("Get page title")
    def get_title(self) -> str:
        """Return the document <title>."""
        return self.page.title()

    @allure.step("Get current URL")
    def get_url(self) -> str:
        """Return the current page URL."""
        return self.page.url

    # ------------------------------------------------------------------
    # Waits
    # ------------------------------------------------------------------

    @allure.step("Wait for element '{selector}' — state='{state}'")
    def wait_for_element(self, selector: str, state: str = "visible", timeout: int = 10000):
        """Wait for an element to reach the given state (visible | attached | hidden | detached)."""
        self.page.locator(selector).first.wait_for(state=state, timeout=timeout)

    @allure.step("Wait for page load state: {state}")
    def wait_for_load_state(self, state: str = "load"):
        """Wait for the page to reach a load state (load | domcontentloaded | networkidle)."""
        self.page.wait_for_load_state(state)

    @allure.step("Wait for network idle")
    def wait_for_network_idle(self):
        """Convenience wrapper — wait until there are no in-flight network requests."""
        self.page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------------
    # Visibility helpers
    # ------------------------------------------------------------------

    def is_element_visible(self, selector: str) -> bool:
        """Return True if the first element matching *selector* is visible."""
        return self.page.locator(selector).first.is_visible()

    def count_elements(self, selector: str) -> int:
        """Return how many elements match *selector*."""
        return self.page.locator(selector).count()

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    @allure.step("Scroll element '{selector}' into view")
    def scroll_into_view(self, selector: str):
        """Scroll until the first matching element is in the viewport."""
        self.page.locator(selector).first.scroll_into_view_if_needed()

    @allure.step("Scroll to bottom of page")
    def scroll_to_bottom(self):
        """Scroll the page to the very bottom."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    @allure.step("Take full-page screenshot")
    def take_screenshot(self, full_page: bool = True) -> bytes:
        """Capture a screenshot and return the raw bytes."""
        return self.page.screenshot(full_page=full_page)
