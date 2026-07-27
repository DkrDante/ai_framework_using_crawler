from playwright.sync_api import sync_playwright

def login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        page = browser.new_page()

        page.goto(
            "https://try.satorixr.com/login",
            wait_until="networkidle"
        )

        page.get_by_placeholder(
            "Enter your email to continue"
        ).fill("piyush@satorixr.com")

        page.get_by_text("Send Verification Code").click()

        # Wait for OTP field to appear
        page.wait_for_selector("input")

        otp = input("Enter OTP received via email: ")

        page.locator("input").fill(otp)

        page.get_by_role("button").click()

        page.wait_for_timeout(10000)

        browser.close()

if __name__ == "__main__":
    login()