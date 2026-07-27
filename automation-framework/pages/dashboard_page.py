"""
DashboardPage — Page Object for the SatoriXR /home dashboard.

Locators + actions only. No assertions.
"""

import re
import allure
from playwright.sync_api import Page, Locator
from pages.base_page import BasePage


class DashboardPage(BasePage):
    """Provides locators and actions for the main dashboard view."""

    def __init__(self, page: Page):
        super().__init__(page)

    # ------------------------------------------------------------------
    # Heading locators
    # ------------------------------------------------------------------

    @allure.step("Get heading with name '{name}'")
    def get_heading(self, name: str) -> Locator:
        """Return a locator for a heading element by accessible name."""
        return self.page.get_by_role("heading", name=name)

    # ------------------------------------------------------------------
    # Metric card locators
    # ------------------------------------------------------------------

    @allure.step("Get metric card by title '{title}'")
    def get_metric_card(self, title: str) -> Locator:
        """
        Locates a metric/stat card by its visible title text within the main content area.
        Uses a broad container selector then filters by title text — resilient to CSS class changes.
        """
        return self.page.locator("main").locator(
            "div"
        ).filter(has_text=re.compile(rf"{re.escape(title)}", re.IGNORECASE)).first

    # ------------------------------------------------------------------
    # Metric card data extraction
    # ------------------------------------------------------------------

    @allure.step("Extract numeric value from metric card '{title}'")
    def get_metric_card_value(self, title: str) -> int | None:
        """
        Return the first integer found in the card's inner text,
        or None if no number is present.
        """
        card = self.get_metric_card(title)
        text = card.inner_text()
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else None

    # ------------------------------------------------------------------
    # product card locators
    # ------------------------------------------------------------------

    @allure.step("Get product cards in the Products section")
    def get_section_product_cards(self) -> list[Locator]:
        """Return a list of locators for the product cards displayed in the Products section."""
        heading = self.get_products_heading()
        container = heading.locator('xpath=../following-sibling::*[1]')
        container.locator("div.p-4.flex.flex-col.flex-1").first.wait_for(state="visible", timeout=10000)
        return container.locator("div.p-4.flex.flex-col.flex-1").all()

    @allure.step("Get Products section heading")
    def get_products_heading(self) -> Locator:
        """Return the H2 heading for the Products section."""
        return self.page.locator('h2:has-text("Products")').first

    @staticmethod
    def get_product_card_details(card: Locator) -> dict:
        """Extract details from a product card Locator."""
        title = card.locator("h3").inner_text().strip()
        exp_text = card.locator("span:has-text('Experiences:')").last.inner_text().strip()
        exp_match = re.search(r"Experiences:\s*(\d+)", exp_text)
        exp_count = int(exp_match.group(1)) if exp_match else 0
        time_text = card.locator("span.ml-auto").inner_text().strip()
        return {
            "name": title,
            "experience_count": exp_count,
            "relative_time": time_text
        }
    
    # ------------------------------------------------------------------
    # Experience card locators
    # ------------------------------------------------------------------

    def get_section_experience_cards(self) -> list[Locator]:
        """Return a list of locators for the experience cards displayed in the Experiences section."""
        heading = self.get_experiences_heading()
        container = heading.locator('xpath=../following-sibling::*[1]')
        container.locator("div.p-4.flex.flex-col.flex-1").first.wait_for(state="visible", timeout=10000)
        return container.locator("div.p-4.flex.flex-col.flex-1").all()

    def get_experiences_heading(self) -> Locator:
        """Return the H2 heading for the Experiences section."""
        return self.page.locator('h2:has-text("Experiences")').first
    
    def get_experience_card_details(self, card: Locator) -> dict:
        """Extract details from an experience card Locator."""
        title = card.locator("h3").inner_text().strip()
        time_text = card.locator("span.ml-auto").inner_text().strip()
        return {
            "name": title,
            "relative_time": time_text
        }

    # ------------------------------------------------------------------
    # Navigation locators
    # ------------------------------------------------------------------

    @allure.step("Get navigation item with name '{name}'")
    def get_nav_item(self, name: str) -> Locator:
        """Return a locator for a sidebar navigation link or button."""
        if name == "Settings":
            return self.page.get_by_role("button", name=name)
        return self.page.get_by_role("link", name=name)

    @allure.step("Get navigation item (fallback) with name '{name}'")
    def get_nav_item_fallback(self, name: str) -> Locator:
        """Fallback — locate by visible text when there is no link role."""
        if name == "Settings":
            return self.page.locator("button").filter(has_text=name)
        return self.page.locator(f"text={name}")

    def get_nav(self, name: str, timeout: int = 2000) -> Locator:
        """
        Smart nav locator — tries by role first, then falls back to
        text-based lookup.
        """
        primary = self.get_nav_item(name)
        try:
            primary.wait_for(state="attached", timeout=timeout)
            return primary
        except Exception:
            fallback = self.get_nav_item_fallback(name)
            try:
                fallback.wait_for(state="attached", timeout=timeout)
                return fallback
            except Exception:
                assert False, f"Navigation item '{name}' not found"
