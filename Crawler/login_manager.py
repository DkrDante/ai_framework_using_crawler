import os
import sys
import asyncio
from shared_utils.logger import get_logger

# Initialize Logger
logger = get_logger("login_manager")

# Login lock to serialize concurrent login attempts
login_lock = asyncio.Lock()

async def ensure_login_state(state_path):
    """
    Checks if session state file exists. If missing, triggers headed browser login
    flow to acquire credentials and write playwrght state context.
    """
    if os.path.exists(state_path):
        return

    async with login_lock:
        # Double check inside lock to prevent redundant login procedures
        if os.path.exists(state_path):
            return

        email_address = os.environ.get("EMAIL_ADDRESS")
        email_password = os.environ.get("EMAIL_PASSWORD")
        
        # If the file doesn't exist and we don't have credentials, we can't login!
        if not email_address or not email_password:
            raise ValueError(
                "Login state file state.json is missing, and EMAIL_ADDRESS / EMAIL_PASSWORD environment variables are not set in .env. "
                "Please configure credentials to generate a new state.json."
            )
            
        logger.info("Login state not found. Running login...")
        try:
            # Ensure workspace root is in python path to resolve modules
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            if root_dir not in sys.path:
                sys.path.append(root_dir)
                
            from Crawler.login.login import login
            # Run login synchronously in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, login, state_path)
            
            # Verify the file was written
            if not os.path.exists(state_path):
                raise FileNotFoundError(f"Login flow completed but state file was not created at {state_path}")
                
            logger.info(f"Login successful! New state saved to {state_path}")
        except Exception as e:
            raise RuntimeError(f"Login flow failed: {e}")
