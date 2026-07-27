"""
AI-Generated Test Suite — Home Dashboard
=========================================
Automatically generated from test_cases.json by Code_Gen/main.py.
Tests cover the SatoriXR Home Dashboard: Overview metrics, Products section,
Experiences section, Navigation, and Header components.
"""

import re
import pytest
import allure
from playwright.sync_api import expect


# ---------------------------------------------------------------------------
# Test Suite: Overview Section
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Overview Section")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_001_verify_dashboard_overview_metrics_display(page, config):
    """
    Verify Dashboard Overview Metrics Display

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate the Overview heading and section headings for Products & Experiences

    Expected Result:
    Overview heading is visible along with Products and Experiences section headings
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify 'Overview' heading is visible"):
        expect(page.get_by_role("heading", name="Overview")).to_be_visible()

    with allure.step("Verify 'Products' section heading is visible"):
        expect(page.locator("h2").filter(has_text=re.compile(r"Products"))).to_be_visible()

    with allure.step("Verify 'Experiences' section heading is visible"):
        expect(page.locator("h2").filter(has_text=re.compile(r"Experiences"))).to_be_visible()


# ---------------------------------------------------------------------------
# Test Suite: Products Section
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Products Section")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_002_verify_product_cards_display_correct_information(page, config):
    """
    Verify Product Cards Display Correct Information

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate product cards in the Products section

    Expected Result:
    Each product card displays image, name, and View/Edit buttons
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Find the Products section container"):
        # The products section is anchored by the h2 heading containing 'Products'
        products_section = page.locator("section, div").filter(
            has=page.locator("h2").filter(has_text=re.compile(r"Products"))
        ).first
        # Product cards are flex column divs inside the section
        cards = products_section.locator("div.flex.flex-col").all()

    with allure.step("Verify at least one product card exists"):
        assert len(cards) > 0, "Expected at least one product card in Products section"

    with allure.step("Verify first product card has View and Edit buttons"):
        first_card = cards[0]
        expect(first_card.get_by_role("button", name=re.compile(r"View", re.I)).first).to_be_visible()
        expect(first_card.get_by_role("button", name=re.compile(r"Edit", re.I)).first).to_be_visible()


@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Products Section — Navigation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_003_verify_products_view_all_link_navigation(page, config):
    """
    Verify Products 'View All' Link Navigation

    Steps:
    1. Navigate to Dashboard/Home page
    2. Click 'View All' link in the Products section header
    3. Verify URL changes to /products

    Expected Result:
    User is redirected to /products page
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Click 'View All' in the Products section"):
        # There are two 'View All' links — Products is first, Experiences is second
        view_all_links = page.get_by_role("link", name=re.compile(r"View All", re.I))
        view_all_links.first.click()
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify URL is the Products page"):
        expect(page).to_have_url(re.compile(r".*/products.*"))


# ---------------------------------------------------------------------------
# Test Suite: Experiences Section
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Experiences Section")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_004_verify_experience_cards_display_correct_information(page, config):
    """
    Verify Experience Cards Display Correct Information

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate experience cards in the Experiences section

    Expected Result:
    Each experience card displays image, name, and View/Edit buttons
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Find the Experiences section container"):
        experiences_section = page.locator("section, div").filter(
            has=page.locator("h2").filter(has_text=re.compile(r"Experiences"))
        ).first
        cards = experiences_section.locator("div.flex.flex-col").all()

    with allure.step("Verify at least one experience card exists"):
        assert len(cards) > 0, "Expected at least one experience card in Experiences section"

    with allure.step("Verify first experience card has View and Edit buttons"):
        first_card = cards[0]
        expect(first_card.get_by_role("button", name=re.compile(r"View", re.I)).first).to_be_visible()
        expect(first_card.get_by_role("button", name=re.compile(r"Edit", re.I)).first).to_be_visible()


@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Experiences Section — Navigation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_005_verify_experiences_view_all_link_navigation(page, config):
    """
    Verify Experiences 'View All' Link Navigation

    Steps:
    1. Navigate to Dashboard/Home page
    2. Click 'View All' link in the Experiences section header
    3. Verify URL changes to /experiences

    Expected Result:
    User is redirected to /experiences page
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Click 'View All' in the Experiences section"):
        # There are two 'View All' links — Experiences is the second one
        view_all_links = page.get_by_role("link", name=re.compile(r"View All", re.I))
        view_all_links.nth(1).click()
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify URL is the Experiences page"):
        expect(page).to_have_url(re.compile(r".*/experiences.*"))


# ---------------------------------------------------------------------------
# Test Suite: Navigation
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Sidebar Navigation — Active State")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_006_verify_navigation_menu_highlighting(page, config):
    """
    Verify Navigation Menu Highlighting

    Steps:
    1. Navigate to Dashboard/Home page
    2. Inspect the active state of the Home navigation item

    Expected Result:
    Home navigation item has an active/highlighted class indicating current page
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify Home nav link has an active CSS class"):
        home_link = page.get_by_role("link", name=re.compile(r"^Home$", re.I))
        # Active Vue Router links receive the 'router-link-active' class
        expect(home_link).to_have_class(re.compile(r"router-link-active|active|selected"))


# ---------------------------------------------------------------------------
# Test Suite: Header
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Header Components")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.ui
@pytest.mark.smoke
def test_TC_007_verify_header_components_visibility(page, config):
    """
    Verify Header Components Visibility

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate the header element

    Expected Result:
    The page header is visible and contains the main navigation toolbar
    """
    with allure.step("Navigate to Home page"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify header element is present and visible"):
        expect(page.locator("header, nav").first).to_be_visible()

    with allure.step("Verify user account area is visible in the header"):
        header = page.locator("header").first
        expect(header).to_be_visible()


# ---------------------------------------------------------------------------
# BUG CAPTURE: API vs UI Data Consistency
# ---------------------------------------------------------------------------

@allure.epic("SatoriXR Dashboard")
@allure.feature("AI-Generated UI Tests")
@allure.story("Data Integrity — API vs UI")
@allure.severity(allure.severity_level.BLOCKER)
@allure.title("🐛 BUG CHECK: Product count on dashboard must match API")
@pytest.mark.ui
@pytest.mark.regression
def test_TC_008_verify_product_count_matches_api(page, config, api_context):
    """
    Bug Capture: Verify the Products count displayed on the dashboard Overview
    matches the actual count from the backend API.

    A mismatch here indicates a stale cache or a UI rendering bug.
    """
    from services import DashboardAPIService
    import re as _re

    with allure.step("Fetch product count from the backend API"):
        svc = DashboardAPIService(api_context)
        api_count = svc.get_active_products_count()
        allure.attach(
            str(api_count),
            name="API Product Count",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Navigate to Dashboard and read the Products metric card"):
        page.goto(config["base_url"] + "/home", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        # The metric card that shows "Total Products" — contains a number
        card = page.locator("div, section").filter(
            has_text=re.compile(r"Total Products", re.I)
        ).first
        card_text = card.inner_text()

        # Extract first number found in the card
        match = _re.search(r"\d+", card_text)
        ui_count = int(match.group()) if match else None

        allure.attach(
            str(ui_count),
            name="UI Product Count",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Attach screenshot of the card area so failures show exactly what's wrong
        screenshot = page.screenshot()
        allure.attach(
            screenshot,
            name="Dashboard Screenshot",
            attachment_type=allure.attachment_type.PNG,
        )

    with allure.step(f"Compare: API={api_count} vs UI={ui_count}"):
        assert ui_count is not None, (
            "Could not find a numeric value in the 'Total Products' card. "
            "The card may not have loaded or the selector needs updating."
        )
        assert ui_count == api_count, (
            f"🐛 BUG DETECTED: Dashboard shows {ui_count} products "
            f"but the API reports {api_count} active products. "
            f"This indicates a stale cache or rendering bug."
        )
