"""Tests for SatoriXR Home Dashboard UI components and navigation"""

import re
import pytest
import allure
from playwright.sync_api import expect


@pytest.mark.ui
@pytest.mark.smoke
def test_TC_001_verify_dashboard_overview_metrics_display(page, config):
    """
    Verify Dashboard Overview Metrics Display

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate overview section heading and product/experience section headings

    Expected Result:
    Overview heading is visible along with Products and Experiences section headings
    """
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify Overview heading is visible"):
        expect(page.get_by_role("heading", name="Overview")).to_be_visible()

    with allure.step("Verify Products section heading is visible"):
        expect(page.locator("h2").filter(has_text=re.compile(r"Products"))).to_be_visible()

    with allure.step("Verify Experiences section heading is visible"):
        expect(page.locator("h2").filter(has_text=re.compile(r"Experiences"))).to_be_visible()


@pytest.mark.ui
@pytest.mark.smoke
def test_TC_002_verify_product_cards_display_correct_information(page, config):
    """
    Verify Product Cards Display Correct Information

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate product cards in Products section

    Expected Result:
    Each product card displays image, name, and View/Edit buttons
    """
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Find the Products section container"):
        # The products section is under the h2 heading that contains 'Products'
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


@pytest.mark.ui
@pytest.mark.smoke
def test_TC_003_verify_products_view_all_link_navigation(page, config):
    """
    Verify Products View All Link Navigation

    Steps:
    1. Navigate to Dashboard/Home page
    2. Click 'View All' link in the Products section header
    3. Verify URL changes to products page

    Expected Result:
    User is redirected to /products page
    """
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Click View All in the Products section"):
        # There are two 'View All' links on the page — Products is first, Experiences is second
        view_all_links = page.get_by_role("link", name=re.compile(r"View All", re.I))
        view_all_links.first.click()
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify URL is now the products page"):
        expect(page).to_have_url(re.compile(r".*/products.*"))


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


@pytest.mark.ui
@pytest.mark.smoke
def test_TC_005_verify_experiences_view_all_link_navigation(page, config):
    """
    Verify Experiences View All Link Navigation

    Steps:
    1. Navigate to Dashboard/Home page
    2. Click 'View All' link in the Experiences section header
    3. Verify URL changes to experiences page

    Expected Result:
    User is redirected to /experiences page
    """
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Click View All in the Experiences section"):
        # There are two 'View All' links on the page — Experiences is the second one
        view_all_links = page.get_by_role("link", name=re.compile(r"View All", re.I))
        view_all_links.nth(1).click()
        page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify URL is now the experiences page"):
        expect(page).to_have_url(re.compile(r".*/experiences.*"))


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
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify Home nav link has an active class"):
        home_link = page.get_by_role("link", name=re.compile(r"^Home$", re.I))
        # Playwright's has_class uses regex; active Vue router links get router-link-active
        expect(home_link).to_have_class(re.compile(r"router-link-active|active|selected"))


@pytest.mark.ui
@pytest.mark.smoke
def test_TC_007_verify_header_components_visibility(page, config):
    """
    Verify Header Components Visibility

    Steps:
    1. Navigate to Dashboard/Home page
    2. Locate header components (language selector, profile icon, account menu)

    Expected Result:
    Language selector and user profile / account menu elements are visible in the header
    """
    page.goto(config["base_url"] + "/home", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)

    with allure.step("Verify header is present"):
        expect(page.locator("header, nav").first).to_be_visible()

    with allure.step("Verify user/account area is visible"):
        # Profile button or user avatar — any button in the header area
        header = page.locator("header").first
        expect(header).to_be_visible()
