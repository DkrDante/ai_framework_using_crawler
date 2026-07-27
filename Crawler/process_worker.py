import asyncio
import os
import json
import shutil
import time
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from shared_utils.logger import get_logger
from Crawler.hooks import create_before_goto_hook, create_after_goto_hook
from Crawler.utils.helpers import (
    register_url_folder,
    should_ignore_element,
    compute_page_signature,
    draw_bounding_boxes,
    is_url_allowed,
    is_element_allowed,
    is_home_page,
    is_create_page,
    is_dropdown
)

logger = get_logger("process_worker")

def get_api_endpoint_key(method, url):
    """
    Generates a normalized key for deduplicating API endpoints.
    Replaces numeric IDs and UUIDs, and removes query parameters.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Replace numeric segments, e.g., /123/ -> /{id}/
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Replace UUID segments, e.g., /123e4567-e89b-12d3-a456-426614174000/ -> /{id}/
        uuid_pattern = r'/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)'
        path = re.sub(uuid_pattern, '/{id}', path)
        
        # Combine scheme, netloc, and normalized path
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        return (method.upper(), normalized_url)
    except Exception:
        return (method.upper(), url)

async def process_page(
    crawler, url, interaction_path, source_state_url, click_info, start_domain,
    config, url_to_folder, visited_signatures, graph_pages, graph_links, graph_lock,
    allowed_clicks, allowed_urls, global_apis
):
    """Processes a single queue item: runs crawl, parses elements, and finds outlinks + button clicks."""
    state_url = url
    if interaction_path:
        suffix = "#state-" + "-".join(str(step["id"]) for step in interaction_path)
        state_url = url + suffix

    folder_name = register_url_folder(url, interaction_path, config['start_url'], url_to_folder)
    page_dir = os.path.join(config['output_dir'], folder_name)
    
    logger.debug(f"[Worker] Starting crawl for: {state_url}")
    
    # Shared list to capture requests between before_goto and after_goto
    captured_requests = []
    
    # Register hooks per crawl run
    crawler.crawler_strategy.set_hook("before_goto", create_before_goto_hook(captured_requests, url))
    crawler.crawler_strategy.set_hook("after_goto", create_after_goto_hook(
        captured_requests, interaction_path, url, config['start_url'], config['output_dir'], url_to_folder, allowed_urls,
        api_only=config.get('api_only', False)
    ))

    # Run config
    run_config = CrawlerRunConfig(
        cache_mode="BYPASS"
    )
    
    try:
        result = await crawler.arun(url=url, config=run_config)
    except Exception as e:
        logger.error(f"[Worker] Exception calling arun for {state_url}: {e}")
        return [], []

    if not result.success:
        logger.error(f"[Worker] Crawl failed for {state_url}: {result.error_message}")
        return [], []

    # Check if redirected url marker is present
    soup = BeautifulSoup(result.html, "html.parser")
    
    # Retrieve APIs from custom container
    apis_div = soup.find(id="extracted-apis-data")
    if apis_div:
        try:
            apis_data = json.loads(apis_div.text)
        except Exception as e:
            logger.error(f"[Worker] Failed to parse APIs JSON: {e}")
            apis_data = {"initial_apis": [], "transition_apis": [], "all_apis": []}
    else:
        apis_data = {"initial_apis": [], "transition_apis": [], "all_apis": []}

    # Aggregate APIs to global list
    all_captured = apis_data.get("all_apis", [])
    async with graph_lock:
        for req in all_captured:
            method = req.get("method", "GET")
            req_url = req.get("url", "")
            if not req_url:
                continue
            key = get_api_endpoint_key(method, req_url)
            if key not in global_apis:
                global_apis[key] = {
                    "url": req_url,
                    "method": method,
                    "headers": req.get("headers"),
                    "post_data": req.get("post_data"),
                    "resource_type": req.get("resource_type"),
                    "response_reference": req.get("response_reference")
                }
            else:
                if not global_apis[key].get("headers") and req.get("headers"):
                    global_apis[key]["headers"] = req["headers"]
                if not global_apis[key].get("post_data") and req.get("post_data"):
                    global_apis[key]["post_data"] = req["post_data"]
                if not global_apis[key].get("response_reference") and req.get("response_reference"):
                    global_apis[key]["response_reference"] = req["response_reference"]

    redirect_div = soup.find(id="redirected-url-marker")
    if redirect_div:
        target_url = redirect_div.text.strip()
        logger.debug(f"[Worker] Detected navigation-away to: {target_url} for state {state_url}")

        # Add transition from source_state_url to target_url (NO APIs)
        if source_state_url and click_info:
            edge = {
                "source": source_state_url,
                "target": target_url,
                "text": click_info.get("text", ""),
                "element_id": click_info.get("element_id"),
                "locator": click_info.get("locator", "")
            }
            async with graph_lock:
                if edge not in graph_links:
                    graph_links.append(edge)
                    
        # Don't delete the shared URL folder on redirection
        
        # Return target_url as navigational outlink so BFS enqueues it if not visited
        return [target_url], []

    # Retrieve elements from custom container
    page_title = soup.title.text.strip() if soup.title else "No Title"
    
    data_div = soup.find(id="extracted-elements-data")
    if not data_div:
        logger.debug(f"[Worker] Warning: No element extraction data container found in HTML for {state_url}")
        return [], []

    try:
        elements = json.loads(data_div.text)
        elements = [el for el in elements if not should_ignore_element(el)]
    except Exception as e:
        logger.error(f"[Worker] Failed to parse elements JSON for {state_url}: {e}")
        return [], []

    # Calculate page signature
    sig = compute_page_signature(elements)
    sig_key = f"{url}||{sig}"
    
    # Lock for thread-safety when updating signature map and graph
    async with graph_lock:
        if sig_key in visited_signatures:
            existing_state_url = visited_signatures[sig_key]
            logger.debug(f"[Worker] State signature match! {state_url} matches {existing_state_url}. Grouping captures.")
            
            # Map this URL to the duplicate's folder
            parsed_state = urlparse(state_url)
            base_state = parsed_state._replace(fragment="", query="").geturl()
            parsed_existing = urlparse(existing_state_url)
            base_existing = parsed_existing._replace(fragment="", query="").geturl()
            if base_existing in url_to_folder:
                url_to_folder[base_state] = url_to_folder[base_existing]
            
            # Add transition from source_state_url to existing_state_url (NO APIs)
            if source_state_url and click_info:
                edge = {
                    "source": source_state_url,
                    "target": existing_state_url,
                    "text": click_info.get("text", ""),
                    "element_id": click_info.get("element_id"),
                    "locator": click_info.get("locator", "")
                }
                if edge not in graph_links:
                    graph_links.append(edge)
            
            # Don't delete the shared URL folder on duplicate signature
            return [], []

        # Mark signature as visited
        visited_signatures[sig_key] = state_url
        
        # Add to pages (NO APIs)
        graph_pages.append({
            "url": state_url,
            "folder": folder_name,
            "title": page_title,
            "element_count": len(elements)
        })

        # Add transition from source_state_url to state_url (NO APIs)
        if source_state_url and click_info:
            edge = {
                "source": source_state_url,
                "target": state_url,
                "text": click_info.get("text", ""),
                "element_id": click_info.get("element_id"),
                "locator": click_info.get("locator", "")
            }
            if edge not in graph_links:
                graph_links.append(edge)

    # Save details if not api_only
    if not config.get('api_only'):
        elements_json_path = os.path.join(page_dir, "elements.json")
        metadata_json_path = os.path.join(page_dir, "page_info.json")
        screenshot_path = os.path.join(page_dir, "screenshot.png")
        labeled_screenshot_path = os.path.join(page_dir, "screenshot_labeled.png")

        if not os.path.exists(labeled_screenshot_path):
            with open(elements_json_path, "w", encoding="utf-8") as f:
                json.dump(elements, f, indent=4)

            # Draw visual overlays
            if os.path.exists(screenshot_path):
                if len(elements) > 0:
                    try:
                        draw_bounding_boxes(screenshot_path, elements, labeled_screenshot_path)
                        logger.debug(f"[Worker] Saved annotated screenshot: {labeled_screenshot_path}")
                    except Exception as e:
                        logger.error(f"[Worker] Error drawing visual elements overlay: {e}")
                        shutil.copy(screenshot_path, labeled_screenshot_path)
                else:
                    shutil.copy(screenshot_path, labeled_screenshot_path)
                    
                # Remove raw screenshot so we only keep the labeled screenshot
                try:
                    os.remove(screenshot_path)
                except Exception:
                    pass
        else:
            logger.debug(f"[Worker] Labeled screenshot already exists for {folder_name}. Skipping overwrite.")

    # 1. Discover Navigational outlinks
    discovered_links = []
    for el in elements:
        if should_ignore_element(el):
            continue
        href = el.get("attributes", {}).get("href")
        if not href:
            continue
        
        # Resolve path
        resolved_url = urljoin(url, href)
        parsed_res = urlparse(resolved_url)
        target_normalized = parsed_res._replace(fragment="").geturl()

        # Constraints
        if parsed_res.netloc != start_domain:
            continue

        # Check blacklist
        url_lower = target_normalized.lower()
        logout_keywords = ["logout", "signout", "sign-out", "exit", "log-out", "login", "sign-in", "signin"]
        if any(kw in url_lower for kw in logout_keywords):
            continue

        # Check if URL is allowed based on test case constraints
        if not is_url_allowed(target_normalized, allowed_urls, source_url=url):
            continue

        edge = {
            "source": state_url,
            "target": target_normalized,
            "text": el.get("text", ""),
            "element_id": el.get("id"),
            "locator": el.get("playwright_locator", "")
        }
        
        async with graph_lock:
            if edge not in graph_links:
                graph_links.append(edge)

        discovered_links.append(target_normalized)

    # 2. Discover button clicks for dynamic state changes (if depth is within max_depth limit)
    discovered_clicks = []
    
    # Check if this URL is one of the main seed URLs.
    # If it is not a main seed URL (e.g., it is a sub-link like /product/create), we backtrack (do not explore clicks).
    parsed_current = urlparse(url)
    current_path_clean = parsed_current.path.strip("/").lower()
    
    is_main_url = False
    if allowed_urls:
        for allowed in allowed_urls:
            if current_path_clean == allowed.strip("/").lower():
                is_main_url = True
                break
    else:
        is_main_url = True
        
    if len(interaction_path) < config['max_depth'] and is_main_url:
        is_home = is_home_page(url)
        is_create = is_create_page(url)
        clickable_candidates = []
        for el in elements:
            if should_ignore_element(el):
                continue
                
            # Skip if it is a dropdown, except Settings
            if is_dropdown(el):
                text_lower = el.get("text", "").strip().lower()
                if "settings" not in text_lower:
                    continue
                
            tag = el.get("tag", "").lower()
            role = el.get("attributes", {}).get("role", "").lower()
            href = el.get("attributes", {}).get("href")
            
            # Skip standard outlinks
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                continue
                
            # Skip standard inputs
            if tag in ["input", "textarea", "select", "label"] and role not in ["button", "link", "tab"]:
                continue
                
            # Skip disabled or readonly
            if el.get("states", {}).get("disabled") or el.get("states", {}).get("readonly"):
                continue
                
            # Skip if logout/exit/login keywords present
            text_lower = (el.get("text", "") + " " + el.get("playwright_locator", "")).lower()
            logout_keywords = ["logout", "signout", "sign-out", "exit", "log-out", "login", "sign-in", "signin"]
            if any(kw in text_lower for kw in logout_keywords):
                continue
                
            # Skip if selector is empty
            selector = el.get("selector")
            if not selector:
                continue
                
            # Skip if already clicked in this path
            if any(step["selector"] == selector for step in interaction_path):
                continue
                
            # Apply dynamic test case constraints if available, otherwise fallback to hardcoded rules
            if allowed_clicks is not None:
                if not is_element_allowed(el, allowed_clicks):
                    continue
            else:
                # Custom constraint:
                # - On /home, only click the Settings button.
                # - On /product/create and /experience/create, only click the step tabs.
                # - On other pages, skip all clicks.
                if is_home:
                    if el.get("text", "").strip().lower() != "settings":
                        continue
                elif is_create:
                    allowed_texts = ["basic details", "3d asset", "knowledge data", "edit 3d", "preview and save", "preview & save"]
                    text_clean = el.get("text", "").strip().lower().replace("\n", " ")
                    if not any(kw in text_clean for kw in allowed_texts):
                        continue
                else:
                    continue
                
            clickable_candidates.append(el)

        logger.debug(f"[Worker] Found {len(clickable_candidates)} clickable buttons for state exploration on {state_url}")
        
        for candidate in clickable_candidates:
            new_step = {
                "id": candidate["id"],
                "selector": candidate["selector"],
                "locator": candidate["playwright_locator"]
            }
            
            new_path = interaction_path + [new_step]
            click_info = {
                "text": candidate.get("text", ""),
                "element_id": candidate.get("id"),
                "locator": candidate.get("playwright_locator", "")
            }
            discovered_clicks.append((url, new_path, state_url, click_info))

    return discovered_links, discovered_clicks

async def worker(
    queue, start_domain, state_path, config, url_to_folder, visited_signatures,
    visited_states, graph_pages, graph_links, graph_lock, allowed_clicks, allowed_urls,
    global_apis
):
    """Coroutine representing an independent crawler worker in the task pool."""
    # Initialize independent BrowserConfig per worker to avoid race conditions
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        storage_state=state_path,
        viewport_width=config['width'],
        viewport_height=config['height']
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            try:
                task = await queue.get()
            except asyncio.CancelledError:
                break

            url, interaction_path, source_state_url, click_info = task
            
            # Determine state representation URL
            state_url = url
            if interaction_path:
                suffix = "#state-" + "-".join(str(step["id"]) for step in interaction_path)
                state_url = url + suffix



            try:
                outlinks, click_tasks = await process_page(
                    crawler, url, interaction_path, source_state_url, click_info, start_domain,
                    config, url_to_folder, visited_signatures, graph_pages, graph_links, graph_lock,
                    allowed_clicks, allowed_urls, global_apis
                )
                
                # Enqueue navigational links (only if allowed by test case URL keywords)
                for link in outlinks:
                    async with graph_lock:
                        link_state = link # base link
                        if link_state not in visited_states:
                            if is_url_allowed(link, allowed_urls, source_url=url):
                                visited_states.add(link_state)
                                await queue.put((link, [], None, None))

                # Enqueue button clicks
                for click_task in click_tasks:
                    click_url, click_path, click_source, click_meta = click_task
                    click_state = click_url + "#state-" + "-".join(str(step["id"]) for step in click_path)
                    async with graph_lock:
                        if click_source and click_meta:
                            edge = {
                                "source": click_source,
                                "target": click_state,
                                "text": click_meta.get("text", ""),
                                "element_id": click_meta.get("element_id"),
                                "locator": click_meta.get("locator", "")
                            }
                            if edge not in graph_links:
                                graph_links.append(edge)
                                
                        if click_state not in visited_states:
                            visited_states.add(click_state)
                            await queue.put((click_url, click_path, click_source, click_meta))
            except Exception as e:
                logger.error(f"[Worker] Error processing state {state_url}: {e}")
            finally:
                queue.task_done()
