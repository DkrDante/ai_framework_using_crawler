import imaplib
import email
import re
import os
import sys
import time
from dotenv import load_dotenv

# Add root path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared_utils.logger import get_logger

# Initialize Logger
logger = get_logger("fetch_otp")

load_dotenv()

def fetch_latest_otp(email_address, password, imap_server="imap.gmail.com"):
    """
    Fetches the latest OTP from the given email inbox.
    """
    try:
        # connect to imap server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select("inbox")

        status, messages = mail.search(None, '(SUBJECT "TRY Login Code")')
        
        if status == "OK" and messages[0]:
            email_ids = messages[0].split() 
            latest_email_id = email_ids[-1] #pick recent one

            # Fetch the email content
            status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
            if status == "OK":
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # parse the email message
                        msg = email.message_from_bytes(response_part[1])
                        
                        # extract the body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain" or content_type == "text/html":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body += payload.decode(errors="ignore")
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                        
                        # strip HTML tags
                        text_body = re.sub(r'<[^>]+>', ' ', body)
                        
                        #find otp
                        match = re.search(r'(\d\s*){6}', text_body)
                        if match:
                            otp_raw = match.group(0)
                            # remove spaces/cleanup
                            otp = re.sub(r'\s+', '', otp_raw)
                            return otp
                            
        logger.warning("No OTP email found.")
        return None

    except Exception as e:
        logger.error(f"Error fetching OTP: {e}")
        return None
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass

if __name__ == "__main__":
    EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        logger.error("Error: EMAIL_ADDRESS and EMAIL_PASSWORD must be configured in environment or .env file.")
    else:
        logger.info("Fetching OTP...")
        otp = fetch_latest_otp(EMAIL_ADDRESS, EMAIL_PASSWORD)
        if otp:
            logger.info(f"Extracted OTP: {otp}")
