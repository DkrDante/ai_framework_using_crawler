"""
LoginPage — Page Object for the SatoriXR login screen.

Locators + actions only. No assertions.
"""

import allure
from playwright.sync_api import Page
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Encapsulates the two-step OTP login flow."""

    # ------------------------------------------------------------------
    # Locators (initialised lazily via properties to survive DOM changes)
    # ------------------------------------------------------------------

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def email_input(self):
        return self.page.locator("#email")

    @property
    def send_otp_button(self):
        return self.page.get_by_role("button", name="Send Verification Code")

    @property
    def otp_input(self):
        return self.page.locator("#otp")

    @property
    def verify_signin_button(self):
        return self.page.get_by_role("button", name="Verify & Sign In")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @allure.step("Fill email input with {email}")
    def fill_email(self, email: str):
        """Enter the user's email address."""
        self.email_input.fill(email)

    @allure.step("Click 'Send Verification Code' button")
    def click_send_otp(self):
        """Request the OTP to be sent."""
        self.send_otp_button.click()

    @allure.step("Fill OTP input")
    def fill_otp(self, otp: str):
        """Enter the received OTP."""
        self.otp_input.fill(otp)

    @allure.step("Click 'Verify & Sign In' button")
    def click_verify_signin(self):
        """Submit the OTP and sign in."""
        self.verify_signin_button.click()

    @allure.step("Perform full OTP login")
    def login_with_otp(self, base_url: str, email: str, otp: str):
        """
        Complete login helper — navigates to the app, fills in
        email + OTP, clicks through, and waits for /home.
        """
        self.navigate(base_url)
        self.fill_email(email)
        self.click_send_otp()
        self.fill_otp(otp)
        self.click_verify_signin()
        self.wait_for_url("**/home")
