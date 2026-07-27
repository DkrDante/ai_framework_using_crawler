import re
import os
import hashlib
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont

def has_word_match(target, text):
    if not target or not text:
        return False
    # Target can have multiple words. Escape it.
    # Match using \b regex word boundaries.
    pattern = r'\b' + re.escape(target.lower()) + r'\b'
    return bool(re.search(pattern, text.lower()))

def is_url_allowed(url, allowed_urls, source_url=None):
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    path_clean = path_lower.strip('/')
    
    # Blacklist login and logout pages completely
    if path_clean in ["login", "logout"]:
        return False

    if not allowed_urls:
        return True

    # Always allow root or home page so crawler can start/proceed
    if path_lower in ["", "/", "/home"]:
        return True
        
    # Check if exact path (stripped of slashes) matches any allowed URL exactly
    for allowed in allowed_urls:
        allowed_clean = allowed.strip('/')
        if path_clean == allowed_clean:
            return True
            
    # Also allow valid sub-links from source_url
    if source_url:
        parsed_source = urlparse(source_url)
        source_path = parsed_source.path.lower()
        if "product" in source_path and "product" in path_lower:
            if "create" in path_clean or "edit" in path_clean:
                return True
        if "experience" in source_path and "experience" in path_lower:
            if "create" in path_clean or "edit" in path_clean:
                return True
        if "settings" in source_path and "settings" in path_lower:
            return True
            
    return False

def is_element_allowed(el, allowed_clicks):
    if not allowed_clicks:
        return True
    
    text = el.get("text", "").strip().lower().replace("\n", " ")
    role = el.get("attributes", {}).get("role", "").lower()
    aria_label = el.get("attributes", {}).get("aria-label", "").lower()
    title = el.get("attributes", {}).get("title", "").lower()
    el_id = el.get("attributes", {}).get("id", "").lower()
    
    # Check if the element text or attributes match any of our allowed click targets under word boundary rules
    for target in allowed_clicks:
        if has_word_match(target, text):
            return True
        if aria_label and has_word_match(target, aria_label):
            return True
        if title and has_word_match(target, title):
            return True
        if el_id and has_word_match(target, el_id):
            return True
            
    # Allow common navigation controls (next, prev, submit, etc.) to ensure multi-step flows work
    common_nav = ["next", "prev", "previous", "submit", "save", "continue", "back", "cancel", "ok"]
    for nav in common_nav:
        if has_word_match(nav, text):
            return True
            
    return False

def get_folder_name(url, base_url):
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    if not path:
        return "root"
    folder_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)
    if parsed_url.query:
        query_sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', parsed_url.query)
        folder_name += "_" + query_sanitized[:30]
    return folder_name

def register_url_folder(url, interaction_path, start_url, url_to_folder):
    parsed = urlparse(url)
    base_url = parsed._replace(fragment="", query="").geturl()

    if base_url in url_to_folder:
        return url_to_folder[base_url]

    folder_name = get_folder_name(base_url, start_url)

    existing_folders = set(url_to_folder.values())
    original = folder_name
    counter = 1
    while folder_name in existing_folders:
        folder_name = f"{original}_{counter}"
        counter += 1

    url_to_folder[base_url] = folder_name
    return folder_name

def compute_page_signature(elements):
    sig_parts = []
    for el in elements:
        tag = el.get("tag", "")
        text = el.get("text", "")
        locator = el.get("playwright_locator", "")
        sig_parts.append(f"{tag}:{text}:{locator}")
    sig_parts.sort()
    sig_str = "||".join(sig_parts)
    return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

def draw_bounding_boxes(image_path, elements, output_path):
    if not os.path.exists(image_path):
        return
    with Image.open(image_path) as img:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        try:
            font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "arial.ttf")
            font = ImageFont.truetype(font_path, 11)
        except Exception:
            font = ImageFont.load_default()

        for el in elements:
            bounds = el.get("bounds")
            if not bounds or len(bounds) != 4:
                continue
            x, y, w, h = bounds
            el_id = str(el.get("id"))
            draw_overlay.rectangle(
                [x, y, x + w, y + h],
                fill=(255, 0, 0, 15),
                outline=(230, 0, 0, 160),
                width=2
            )
            try:
                bbox = draw_overlay.textbbox((x, y), el_id, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except AttributeError:
                tw, th = draw_overlay.textsize(el_id, font=font) if hasattr(draw_overlay, "textsize") else (8, 10)

            pad_x, pad_y = 3, 1
            badge_w, badge_h = tw + pad_x * 2, th + pad_y * 2
            bx = max(0, x)
            by = max(0, y - badge_h)
            draw_overlay.rectangle(
                [bx, by, bx + badge_w, by + badge_h],
                fill=(230, 0, 0, 255)
            )
            draw_overlay.text((bx + pad_x, by + pad_y), el_id, fill=(255, 255, 255, 255), font=font)

        if img.mode != "RGBA":
            img_rgba = img.convert("RGBA")
        else:
            img_rgba = img
        composite = Image.alpha_composite(img_rgba, overlay)
        composite.convert("RGB").save(output_path, "PNG")

def should_ignore_element(el):
    classes = el.get("attributes", {}).get("class", "")
    # Check if this matches the sidebar toggle button
    if "w-7" in classes and "h-7" in classes and "rounded-full" in classes and "bg-white" in classes:
        return True
    return False

def is_dropdown(el):
    tag = el.get("tag", "").lower()
    role = el.get("attributes", {}).get("role", "").lower()
    classes = el.get("attributes", {}).get("class", "").lower()
    aria_haspopup = el.get("attributes", {}).get("aria-haspopup", "").lower()
    
    if tag == "select":
        return True
    if role in ["combobox", "menu", "listbox"]:
        return True
    if aria_haspopup in ["true", "menu", "listbox", "dialog", "grid"]:
        return True
    if "dropdown" in classes:
        return True
    return False

def is_home_page(url):
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip('/')
    return path in ("", "/home")

def is_create_page(url):
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip('/')
    return path in ("/product/create", "/experience/create")
