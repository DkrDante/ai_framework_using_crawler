import os
import imaplib
import email
import re
import time
from datetime import date

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")

# Folders to search in order — covers Gmail Inbox + Spam layouts
_SEARCH_FOLDERS = ["INBOX", '[Gmail]/Spam', "Spam", "Junk"]


def _decode_body(msg) -> str:
    """Extract plain-text body from an email.Message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                if body:
                    break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
    return body


def _extract_otp(body: str):
    """Return the first 6-digit code found in *body*, or None."""
    match = re.search(r"\b(\d{6})\b", body)
    return match.group(1) if match else None


def fetch_otp(
    email_user,
    email_pass,
    subject="Your Satori XR - TRY Login Code",
    retries=15,
    delay=5,
):
    """
    Poll IMAP for an UNSEEN OTP email matching *subject* sent TODAY.

    - Waits 3s before first poll to give the mail server delivery time.
    - Searches INBOX then Spam in case the email is filtered.
    - Only matches UNSEEN emails sent on today's date to avoid reusing
      expired OTPs from previous failed login attempts.
    - Retries up to *retries* x *delay* seconds total.

    Raises Exception with diagnostic info if the OTP is not found.
    """
    # Give mail server a moment to deliver before first check
    time.sleep(3)

    # IMAP SINCE date format: DD-Mon-YYYY
    today_str = date.today().strftime("%d-%b-%Y")

    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(email_user, email_pass)

    for attempt in range(1, retries + 1):
        found_otp = _search_folders(mail, subject, today_str, attempt, retries)
        if found_otp:
            mail.logout()
            return found_otp

        print(f"[OTP] Attempt {attempt}/{retries}: no fresh UNSEEN OTP found. Waiting {delay}s...")
        time.sleep(delay)

    mail.logout()
    raise Exception(
        f"OTP not found after {retries} attempts ({retries * delay}s). "
        f"Subject filter: '{subject}', IMAP host: {IMAP_HOST}, user: {email_user}"
    )


def _search_folders(mail, subject: str, since_date: str, attempt: int, retries: int):
    """Search known folders for a fresh UNSEEN OTP email."""
    _, mailbox_list = mail.list()
    available_raw = " ".join(
        mb.decode(errors="ignore") for mb in mailbox_list if mb
    )

    for folder in _SEARCH_FOLDERS:
        # Skip folders not present on this account (except INBOX which always exists)
        if folder != "INBOX" and folder.strip('"[]') not in available_raw:
            continue

        try:
            quoted = f'"{folder}"' if " " in folder else folder
            status, _ = mail.select(quoted, readonly=False)
            if status != "OK":
                continue
        except Exception:
            continue

        # Search: UNSEEN + subject + sent today
        criteria = f'(UNSEEN SUBJECT "{subject}" SINCE {since_date})'
        status, data = mail.search(None, criteria)
        if status != "OK" or not data or not data[0]:
            continue

        mail_ids = data[0].split()
        if not mail_ids:
            continue

        # Try latest matching email
        for email_id in reversed(mail_ids[-3:]):
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                body = _decode_body(msg)
                otp = _extract_otp(body)
                if otp:
                    mail.store(email_id, "+FLAGS", "\\Seen")
                    print(f"[OTP] Attempt {attempt}/{retries}: found OTP in '{folder}'")
                    return otp
            except Exception:
                continue

    return None