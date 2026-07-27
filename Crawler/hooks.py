import os
import json
import re
from urllib.parse import urlparse
from shared_utils.logger import get_logger
from Crawler.constants.prompts import EXTRACTION_JS
from Crawler.utils.helpers import (
    is_home_page,
    is_create_page,
    register_url_folder,
    is_url_allowed
)

logger = get_logger("hooks")

def truncate_response_reference(data):
    """Recursively truncates lists inside response data to contain at most 1 item."""
    if isinstance(data, list):
        if len(data) > 0:
            return [truncate_response_reference(data[0])]
        return data
    elif isinstance(data, dict):
        truncated = {}
        for k, v in data.items():
            if isinstance(v, list):
                if len(v) > 0:
                    truncated[k] = [truncate_response_reference(v[0])]
                else:
                    truncated[k] = []
            elif isinstance(v, dict):
                truncated[k] = truncate_response_reference(v)
            else:
                truncated[k] = v
        return truncated
    return data

def create_before_goto_hook(captured_requests, task_url):
    """Factory to create a custom before_goto hook that starts listening to responses."""
    async def hook(page, context=None, url=None, **kwargs):
        current_url = url or page.url
        if current_url.rstrip('/') != task_url.rstrip('/'):
            return page

        # Register Playwright page response listener to capture API calls and responses
        async def handle_response(response):
            try:
                req = response.request
                # Filter by prefix and resource type
                if req.resource_type in ["fetch", "xhr"] and req.url.startswith("https://try.satorixr.com/api/"):
                    # Ignore auth/verify-token
                    if "auth/verify-token" in req.url:
                        return
                    
                    # Ignore detail pages for products, scenes, and experiences (anything deeper than the base path)
                    parsed_req_url = urlparse(req.url)
                    req_path = parsed_req_url.path.lower().rstrip('/')
                    if (re.match(r'^/api/products/.+$', req_path) or 
                        re.match(r'^/api/scenes/.+$', req_path) or 
                        re.match(r'^/api/experiences/.+$', req_path)):
                        return
                    
                    # Capture request details
                    post_data = req.post_data
                    if post_data:
                        try:
                            post_data = json.loads(post_data)
                        except Exception:
                            pass
                    
                    # For GET request, capture payload reference from response body
                    response_reference = None
                    if req.method.upper() == "GET":
                        try:
                            text = await response.text()
                            try:
                                resp_json = json.loads(text)
                                response_reference = truncate_response_reference(resp_json)
                            except Exception:
                                response_reference = text[:200]
                        except Exception:
                            pass

                    captured_requests.append({
                        "url": req.url,
                        "method": req.method,
                        "headers": req.headers,
                        "post_data": post_data,
                        "resource_type": req.resource_type,
                        "response_reference": response_reference
                    })
            except Exception:
                pass

        page.on("response", handle_response)
        return page
    return hook

def create_after_goto_hook(captured_requests, interaction_path, task_url, start_url, output_dir, url_to_folder, allowed_urls=None, api_only=False):
    """Factory to create a custom after_goto hook with a bound interaction path."""
    async def hook(page, url=None, context=None, response=None, config=None, **kwargs):
        current_url = url or page.url
        
        # Check if the URL is allowed. If not, skip hook execution
        if allowed_urls is not None and not is_url_allowed(current_url, allowed_urls, source_url=task_url):
            logger.debug(f"[Hook] Navigated to unallowed URL: {current_url} (source: {task_url}). Skipping hook.")
            return page

        if current_url.rstrip('/') != task_url.rstrip('/'):
            return page

        logger.debug(f"[Hook] Navigation complete: {current_url}. Waiting 2 seconds for initial load...")
        await page.wait_for_timeout(2000)

        # Record initial load requests
        initial_apis = list(captured_requests)
        transition_apis = []

        # 1. Click Settings button first if visible to reveal sub-menu (only on home page)
        if is_home_page(current_url):
            try:
                settings_button = page.get_by_role("button", name="Settings", exact=True)
                if await settings_button.is_visible():
                    logger.debug(f"[Hook] Clicking Settings button on {current_url} to reveal sub-menu...")
                    await settings_button.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                pass

        # Fill in dummy values on product/create to pass validation
        if "product/create" in current_url:
            logger.debug("[Hook] Filling form on product/create to pass validation...")
            try:
                name_input = page.locator('input[placeholder*="name"], input[name*="name"], input[id*="name"]')
                if await name_input.count() > 0:
                    await name_input.first.fill("Test Product")
                cat_select = page.locator('select')
                if await cat_select.count() > 0:
                    await cat_select.first.select_option(index=1)
                if await cat_select.count() > 1:
                    await cat_select.nth(1).select_option(index=1)
                desc_textarea = page.locator('textarea')
                if await desc_textarea.count() > 0:
                    await desc_textarea.first.fill("Test Description")
            except Exception as e:
                logger.debug(f"[Hook] Warning: Failed to fill form on product/create: {e}")

        # Fill in dummy values on experience/create to pass validation
        if "experience/create" in current_url:
            logger.debug("[Hook] Filling form on experience/create to pass validation...")
            try:
                inputs = page.locator('input')
                for i in range(await inputs.count()):
                    val = await inputs.nth(i).input_value()
                    if not val:
                        await inputs.nth(i).fill(f"Test Input {i}")
                cat_select = page.locator('select')
                if await cat_select.count() > 0:
                    await cat_select.first.select_option(index=1)
                desc_textarea = page.locator('textarea')
                if await desc_textarea.count() > 0:
                    await desc_textarea.first.fill("Test Description")
            except Exception as e:
                logger.debug(f"[Hook] Warning: Failed to fill form on experience/create: {e}")

        # 2. Replay the interaction path to reach the dynamic sub-state
        navigated_away = False
        navigated_to_url = ""

        for i, step in enumerate(interaction_path):
            selector = step["selector"]
            logger.debug(f"[Hook] Replaying step [{i+1}/{len(interaction_path)}]: click '{selector}'")
            
            # Count requests before the click
            pre_click_count = len(captured_requests)
            
            try:
                loc = page.locator(selector)
                await loc.wait_for(state="visible", timeout=5000)
                await loc.click()
                await page.wait_for_load_state("networkidle", timeout=5000)
                await page.wait_for_timeout(1500) # Wait 1.5 seconds for visual changes
                
                # Count requests after the click
                post_click_count = len(captured_requests)
                step_requests = captured_requests[pre_click_count:post_click_count]
                
                if i == len(interaction_path) - 1:
                    transition_apis = step_requests
                
                # Check if click changed the base URL path (navigated away)
                post_url = page.url
                parsed_post = urlparse(post_url)
                post_url_normalized = parsed_post._replace(fragment="").geturl()
                
                parsed_task = urlparse(task_url)
                task_url_normalized = parsed_task._replace(fragment="").geturl()
                
                if post_url_normalized.rstrip('/') != task_url_normalized.rstrip('/'):
                    logger.debug(f"[Hook] Click navigated away to a new URL: {post_url_normalized}")
                    navigated_away = True
                    navigated_to_url = post_url_normalized
                    break
            except Exception as e:
                logger.debug(f"[Hook] Warning: Failed to click selector '{selector}': {e}")

        # Write API data directly to DOM inside a hidden container
        apis_data = {
            "initial_apis": initial_apis,
            "transition_apis": transition_apis,
            "all_apis": list(captured_requests)
        }
        
        await page.evaluate("""
            (data) => {
                const old = document.getElementById('extracted-apis-data');
                if (old) old.remove();
                const div = document.createElement('div');
                div.id = 'extracted-apis-data';
                div.style.display = 'none';
                div.textContent = JSON.stringify(data);
                document.body.appendChild(div);
            }
        """, apis_data)

        # If we navigated away, write a special redirected marker to the DOM and skip extraction
        if navigated_away:
            await page.evaluate("""
                (targetUrl) => {
                    const old = document.getElementById('redirected-url-marker');
                    if (old) old.remove();
                    const div = document.createElement('div');
                    div.id = 'redirected-url-marker';
                    div.style.display = 'none';
                    div.textContent = targetUrl;
                    document.body.appendChild(div);
                }
            """, navigated_to_url)
            return page

        # Run elements extraction
        try:
            elements = await page.evaluate(EXTRACTION_JS)
            logger.debug(f"[Hook] Extracted {len(elements)} elements from {current_url} (state depth: {len(interaction_path)})")
        except Exception as e:
            logger.error(f"[Hook] Error extracting elements from {current_url}: {e}")
            elements = []

        # Write elements JSON directly to DOM inside a hidden container
        await page.evaluate("""
            (data) => {
                const old = document.getElementById('extracted-elements-data');
                if (old) old.remove();
                const div = document.createElement('div');
                div.id = 'extracted-elements-data';
                div.style.display = 'none';
                div.textContent = JSON.stringify(data);
                document.body.appendChild(div);
            }
        """, elements)

        # Determine save paths and capture screenshot if not api_only
        if not api_only:
            folder_name = register_url_folder(task_url, interaction_path, start_url, url_to_folder)
            page_dir = os.path.join(output_dir, folder_name)
            os.makedirs(page_dir, exist_ok=True)

            screenshot_path = os.path.join(page_dir, "screenshot.png")
            labeled_screenshot_path = os.path.join(page_dir, "screenshot_labeled.png")
            if os.path.exists(labeled_screenshot_path):
                logger.debug(f"[Hook] Folder {folder_name} already contains a labeled screenshot. Skipping screenshot capture to prevent overwrite.")
                return page

            try:
                await page.screenshot(path=screenshot_path)
                logger.debug(f"[Hook] Saved screenshot: {screenshot_path}")
            except Exception as e:
                logger.error(f"[Hook] Failed to capture screenshot for {current_url}: {e}")

        return page
    return hook
