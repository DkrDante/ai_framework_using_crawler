import os
import sys
import re
import json
import urllib.request
from shared_utils.logger import get_logger
from Crawler.constants.prompts import CONSTRAINT_SYSTEM_PROMPT

logger = get_logger("constraint_extractor")

def load_test_cases_constraints(test_cases_path):
    """
    Parses test cases from JSON format and extracts path and click constraints.
    Uses exact quote / capitalization heuristics and URL parsing.
    """
    if not test_cases_path:
        raise ValueError("Test cases path must be provided.")
        
    if not os.path.exists(test_cases_path):
        raise FileNotFoundError(f"Required test cases file not found at: {test_cases_path}")

    try:
        with open(test_cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse test cases JSON file at {test_cases_path}: {e}")

    test_cases = data.get("test_cases", [])
    if not test_cases:
        raise ValueError(f"The test cases list in {test_cases_path} is empty. Cannot proceed.")

    # Extract exact URL paths from the test cases URL fields & text content
    from urllib.parse import urlparse
    import re
    
    exact_urls = set()
    for tc in test_cases:
        tc_url = tc.get("url")
        if tc_url:
            parsed = urlparse(tc_url)
            exact_urls.add(parsed.path.strip("/").lower())
            
    # Also extract any other URLs mentioned in the text fields of the JSON file
    try:
        with open(test_cases_path, "r", encoding="utf-8") as f:
            content = f.read()
        urls = re.findall(r'https?://[a-zA-Z0-9./_-]+', content)
        for u in urls:
            parsed = urlparse(u)
            if "satorixr" in parsed.netloc or not parsed.netloc:
                  exact_urls.add(parsed.path.strip("/").lower())
    except Exception as e:
        logger.error(f"Error extracting additional URLs: {e}")

    # --- Heuristic Fallback ---
    allowed_clicks = set()
    allowed_urls = set()

    stop_words = {
        "step", "verify", "confirm", "click", "enter", "inspect", "select", "system", 
        "url", "email", "verification", "code", "user", "dashboard", "page", "section",
        "and", "the", "for", "with", "from", "to", "in", "on", "at", "as", "is", "are", 
        "a", "an", "this", "that", "it", "its", "their", "different", "valid", "invalid",
        "empty", "input", "field", "button", "link", "text", "address", "registered",
        "status", "unauthorized", "authorized", "authenticated", "authentication",
        "admin", "non-admin", "role", "access", "control", "security", "overview"
    }

    for tc in test_cases:
        text_sources = []
        if isinstance(tc.get("steps"), list):
            text_sources.extend(tc["steps"])
        if isinstance(tc.get("preconditions"), list):
            text_sources.extend(tc["preconditions"])
        if tc.get("title"):
            text_sources.append(tc["title"])

        for text in text_sources:
            # Match quotes as exact click phrases & URL path keywords
            quotes = re.findall(r"['\"]([^'\"]+)['\"]", text)
            for q in quotes:
                q_clean = q.strip().lower()
                if q_clean and q_clean not in stop_words:
                    allowed_clicks.add(q_clean)
                    # Use the clean phrase as URL path clue
                    allowed_urls.add(q_clean)
            
            # Match capitalized phrases as exact click phrases & URL path keywords
            words = re.findall(r"\b[A-Z][a-zA-Z0-9_-]*(?:\s+[A-Z][a-zA-Z0-9_-]*)*\b", text)
            for w in words:
                w_clean = w.strip().lower()
                if w_clean and w_clean not in stop_words:
                    allowed_clicks.add(w_clean)
                    allowed_urls.add(w_clean)

    if not allowed_clicks:
        raise ValueError(f"No valid click constraints or keywords could be extracted from {test_cases_path}.")

    allowed_urls = exact_urls
    logger.info(f"[Constraints] Loaded {len(allowed_clicks)} click target patterns: {list(allowed_clicks)}")
    logger.info(f"[Constraints] Loaded {len(allowed_urls)} URL path keyword clues: {list(allowed_urls)}")
    
    return allowed_clicks, allowed_urls
