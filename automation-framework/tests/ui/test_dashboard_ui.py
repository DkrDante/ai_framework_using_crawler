"""
Dashboard UI Test Suite

Each test validates exactly ONE thing (atomic tests).
Uses DashboardPage page object and test_data constants exclusively.

Naming convention:
    test_<area>_<what_is_being_checked>
"""

import re
import pytest
import allure
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage
from services import DashboardAPIService
from test_data.dashboard_data import (
    DASHBOARD_URL_PATTERN,
    OVERVIEW_HEADING,
    EXPECTED_CARDS,
    EXPECTED_NAV_ITEMS,
    EXPECTED_SUB_NAV_ITEMS,
)



# ---------------------------------------------------------------------------
# Fixtures — setup via page objects, not raw locators
# ---------------------------------------------------------------------------

@pytest.fixture
def module_page(browser, browser_context_args, config):
    """
    Function-scoped page that navigates to the dashboard for each test.
    This ensures complete test isolation and proper video attachment on failure.
    """
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    
    dashboard = DashboardPage(page)
    dashboard.navigate(config["base_url"])
    dashboard.wait_for_url("**/home")
    dashboard.get_heading(OVERVIEW_HEADING).first.wait_for(
        state="visible", timeout=20000
    )
    # Wait for async API calls (stat cards, etc.) to finish loading
    page.wait_for_load_state("networkidle", timeout=30000)
    yield page
    context.close()


@pytest.fixture
def dashboard(module_page):
    """Return a DashboardPage instance bound to the shared module page."""
    return DashboardPage(module_page)


@pytest.fixture
def dashboard_api(api_context):
    """Return a DashboardAPIService for API-vs-UI comparison tests."""
    return DashboardAPIService(api_context)


# ---------------------------------------------------------------------------
# Page basics — one assertion per test
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Page Basics")
@pytest.mark.ui
class TestDashboardPageBasics:
    """Basic page-level sanity checks."""

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_page_title_contains_product_name(self, dashboard):
        """The browser tab title should contain 'SatoriXR'."""
        title = dashboard.get_title()
        assert "SatoriXR" in title, (
            f"Expected 'SatoriXR' in page title, got: '{title}'"
        )

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_url_resolves_to_home_route(self, dashboard):
        """After login the URL should match the /home pattern."""
        url = dashboard.get_url()
        assert DASHBOARD_URL_PATTERN.match(url), (
            f"Expected URL to match '{DASHBOARD_URL_PATTERN.pattern}', got: '{url}'"
        )

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    def test_no_error_banners_on_load(self, dashboard):
        """No generic error banners should be visible on the dashboard."""
        error_locator = dashboard.locator(
            "text=error, text=something went wrong, text=404"
        )
        assert error_locator.count() == 0, (
            "An error message is visible on the dashboard."
        )


# ---------------------------------------------------------------------------
# Overview section — one assertion per test
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Overview Section")
@pytest.mark.ui
class TestOverviewSection:
    """Validates the Overview heading."""

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_overview_heading_is_visible(self, dashboard):
        """The 'Overview' heading must be visible."""
        heading = dashboard.get_heading(OVERVIEW_HEADING)
        expect(heading).to_be_visible(timeout=10000)

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    def test_overview_heading_text_is_exact(self, dashboard):
        """The heading should read exactly 'Overview'."""
        heading = dashboard.get_heading(OVERVIEW_HEADING).first
        heading.wait_for(state="visible", timeout=10000)
        actual = heading.inner_text().strip()
        assert actual == OVERVIEW_HEADING, (
            f"Expected heading '{OVERVIEW_HEADING}', got '{actual}'"
        )


# ---------------------------------------------------------------------------
# Summary cards — parametrized = one test run per card
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Metric Cards")
@pytest.mark.ui
class TestSummaryCards:
    """Validates metric cards. Each parametrized run = one card = one assertion."""

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.parametrize("card_title", EXPECTED_CARDS)
    def test_card_is_visible(self, dashboard, card_title):
        """The metric card should be visible on the dashboard."""
        card = dashboard.get_metric_card(card_title)
        expect(card).to_be_visible()

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    @pytest.mark.parametrize("card_title", EXPECTED_CARDS)
    def test_card_displays_a_number(self, dashboard, card_title):
        """The metric card should contain at least one digit."""
        card = dashboard.get_metric_card(card_title)
        expect(card).to_contain_text(re.compile(r"\d+"), timeout=15000)


# ---------------------------------------------------------------------------
# API-vs-UI consistency — single comparison assertion
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("API vs UI Data Integrity")
@pytest.mark.ui
@pytest.mark.api
class TestApiUiConsistency:
    """Cross-layer validation between API data and UI display."""

    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("🐛 BUG CHECK: Dashboard Products card must match API count")
    @pytest.mark.regression
    def test_products_card_matches_api_count(self, dashboard, module_page, dashboard_api):
        """The 'Total Products' card value should equal the API active count."""
        with allure.step("Fetch active products count from API"):
            api_count = dashboard_api.get_active_products_count()
            allure.attach(
                str(api_count),
                name="API Active Products Count",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Extract numeric value from 'Total Products' card"):
            ui_count = dashboard.get_metric_card_value("Total Products")
            allure.attach(
                str(ui_count),
                name="UI Displayed Products Count",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Capture screenshot of dashboard at time of check"):
            screenshot = module_page.screenshot()
            allure.attach(
                screenshot,
                name="Dashboard at Assertion Time",
                attachment_type=allure.attachment_type.PNG,
            )

        assert ui_count is not None, (
            "Could not extract a numeric value from the 'Total Products' card."
        )
        assert ui_count == api_count, (
            f"UI shows {ui_count} products but API returned {api_count}."
        )


# ---------------------------------------------------------------------------
# Sidebar navigation — parametrized = one test run per nav item
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Sidebar Navigation")
@pytest.mark.ui
class TestSidebarNavigation:
    """Validates sidebar nav items. Each parametrized run = one item."""

    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.parametrize("nav_label", EXPECTED_NAV_ITEMS)
    def test_nav_item_is_visible(self, dashboard, nav_label):
        """The navigation item should be visible in the sidebar."""
        nav = dashboard.get_nav(nav_label)
        expect(nav.first).to_be_visible()

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.regression
    @pytest.mark.parametrize("sub_nav_label", EXPECTED_SUB_NAV_ITEMS)
    def test_settings_sub_nav_item_is_visible(self, dashboard, sub_nav_label):
        """Clicking the Settings button should reveal the sub-navigation item."""
        settings_button = dashboard.get_nav("Settings")
        settings_button.click()
        sub_item = dashboard.get_nav(sub_nav_label)
        expect(sub_item).to_be_visible()
        

# ---------------------------------------------------------------------------
# Products section
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Products Section — Data Integrity")
@pytest.mark.ui
class TestProductDisplay:
    """
    This class contains tests for the Products section of the dashboard.
    """

    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("🐛 BUG CHECK: Products section shows the correct latest 4 products")
    @pytest.mark.regression
    def test_products_section_displays_latest_four_products(self, dashboard, dashboard_api):
        """The Products section should display exactly the latest four products from the API sorted by date."""
        with allure.step("Fetch active products from API and sort descending by date"):
            products = dashboard_api.get_active_products()
            sorted_api_products = sorted(products, key=lambda p: p.get("date", ""), reverse=True)
            expected_latest_four = sorted_api_products[:4]

        with allure.step("Get product cards from Products section"):
            ui_cards = dashboard.get_section_product_cards()
            assert len(ui_cards) == 4, (
                f"Expected exactly 4 product cards in the UI, but found {len(ui_cards)}."
            )

        with allure.step("Verify each card details match the expected latest products in order"):
            for index, card in enumerate(ui_cards):
                ui_details = dashboard.get_product_card_details(card)
                expected_product = expected_latest_four[index]
                
                # Check that name matches
                assert ui_details["name"].strip() == expected_product["name"].strip(), (
                    f"Product at index {index} has mismatch name. "
                    f"Expected: '{expected_product['name']}', Got: '{ui_details['name']}'"
                )

                
                # Check that experience count matches
                assert ui_details["experience_count"] == expected_product["experienceCount"], (
                    f"Product '{expected_product['name']}' at index {index} has mismatch experience count. "
                    f"Expected: {expected_product['experienceCount']}, Got: {ui_details['experience_count']}"
                )    


# ---------------------------------------------------------------------------
# Experience section
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("UI Tests")
@allure.story("Experiences Section — Data Integrity")
@pytest.mark.ui
class TestExperiencesSection:
    """
    This class contains tests for the Experiences section of the dashboard.
    """

    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("🐛 BUG CHECK: Experiences section shows the correct latest 4 experiences")
    @pytest.mark.regression
    def test_experiences_section_displays_latest_four_experiences(self, dashboard, dashboard_api):
        """The Experiences section should display exactly the latest four experiences from the API sorted by date."""
        with allure.step("Fetch active experiences from API and sort descending by date"):
            experiences = dashboard_api.get_active_experiences()
            # Sort descending by date to get the latest experiences
            sorted_api_experiences = sorted(experiences, key=lambda e: e.get("date", ""), reverse=True)
            expected_latest_four = sorted_api_experiences[:4]

        with allure.step("Get experience cards from Experiences section"):
            ui_cards = dashboard.get_section_experience_cards()
            assert len(ui_cards) == 4, (
                f"Expected exactly 4 experience cards in the UI, but found {len(ui_cards)}."
            )

        with allure.step("Verify each card details match the expected latest experiences in order"):
            for index, card in enumerate(ui_cards):
                ui_details = dashboard.get_experience_card_details(card)
                expected_experience = expected_latest_four[index]
                
                # Check that name matches
                assert ui_details["name"] == expected_experience["name"], (
                    f"Experience at index {index} has mismatch name. "
                    f"Expected: '{expected_experience['name']}', Got: '{ui_details['name']}'"
                )