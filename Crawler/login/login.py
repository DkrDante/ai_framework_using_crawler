import os
import sys
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Add root path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared_utils.logger import get_logger

# Initialize Logger
logger = get_logger("login")

try:
    from Crawler.login.fetchOTP import fetch_latest_otp
except ModuleNotFoundError:
    try:
        from login.fetchOTP import fetch_latest_otp
    except ModuleNotFoundError:
        from fetchOTP import fetch_latest_otp

load_dotenv()

def login(state_path="login/state.json"):
    email_address = os.environ.get("EMAIL_ADDRESS")
    email_password = os.environ.get("EMAIL_PASSWORD")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto("https://try.satorixr.com/login")
        page.get_by_placeholder("Enter your email to continue").fill(email_address)
        page.get_by_text("Send Verification Code").click()
        logger.info("Waiting for OTP...")
        page.wait_for_timeout(5000)
        
        otp = None
        for _ in range(10): 
            otp = fetch_latest_otp(email_address, email_password)
            if otp:
                break
            time.sleep(3)
            
        if otp:
            logger.info(f"OTP received: {otp}")

            page.get_by_text("Enter the verification code").wait_for(state="visible")
            page.locator("input").first.focus()
            page.keyboard.type(otp)
            page.get_by_text("Verify & Sign In").click()
            page.wait_for_timeout(5000)
            
            # Ensure output directory for state file exists
            state_dir = os.path.dirname(state_path)
            if state_dir:
                os.makedirs(state_dir, exist_ok=True)
            # Save storage state
            page.context.storage_state(path=state_path)
            logger.info(f"Login state saved to {state_path}")
        else:
            logger.error("Failed to receive OTP.")
        
        # browser.close()

if __name__ == "__main__":
    login()
