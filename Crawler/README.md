# Test-Case Guided Visual Crawler (`Crawler`)

This sub-module visualizes, validates, and logs web portal states asynchronously using `crawl4ai` and Playwright. Rather than crawling a web application blindly, this crawler limits page discovery and interaction paths strictly to flows defined in a structured suite of test cases, preventing infinite search spaces.

---

## File Structure & Module Map

- [crawl_graph.py]: Main module entrypoint. Orchestrates BFS parallel queues, sets up global configuration objects, handles shutdown logic, and exports the final [site_graph.json] transition layout.
- [constraint_extractor.py]: Requirements parser. Decodes the generated JSON test suite, executing Ollama prompts to construct constrained click and path filters. Offers a heuristic backup using quote and uppercase match regexes.
- [process_worker.py]: Crawler BFS worker loops. Manages instances of AsyncWebCrawler, enqueues newly discovered states, checks depth constraints, and structures folder properties.
- [hooks.py]: Playwright runtime lifecycles. Intercepts request paths to list network APIs, fills dynamic fields on forms (such as product title or selector options) to satisfy required validators, and injects extraction JavaScript scripts into browser environments.
- [login_manager.py]: Lock-protected session manager. Serializes access to login flows, ensuring a single worker acquires and saves credentials to avoid parallel logins.
- [login/login.py]: Automates form entry on login pages using Playwright, trigger codes, and awaits OTP retrieval.
- [login/fetchOTP.py]: Connects to the user's Gmail mailbox via IMAP SSL to parse security subjects (`"TRY Login Code"`) and return the 6-digit numeric login code.
- [utils/helpers.py]: Support functions. Formats relative URL paths into alphanumeric folder safe targets, compares boundaries using regex, generates MD5 content signatures, and draws bounding box rectangles onto screenshots via the Python Pillow library.

---

## CLI Reference

Run the crawler from the root workspace using:
```bash
python Crawler/crawl_graph.py [options]
```

### Options

| Command Option | Default Value | Description |
| :--- | :--- | :--- |
| `--url <string>` | `https://try.satorixr.com/home` | The starting URL path for crawler exploration. |
| `--output <path>` | `output` | Folder where visual state folders and transition graphs are saved. |
| `--concurrency <num>`| `3` | Maximum number of concurrent async worker tasks running. |
| `--max-depth <num>` | `1` | Depth limit for click interaction sequences. |
| `--test-cases <path>`| `output/test_cases.json` | Path to the test cases JSON file defining the crawl scope. |
| `--no-llm` | *Flag (Off by default)* | Disables Ollama constraints extraction and falls back to heuristics. |

---

## Core Technical Concepts

### 1. Pre-Crawl LLM-Guided Constraints
To avoid crawling the whole site, the crawler reads test cases and queries Ollama to construct a localized scope:
- **`allowed_urls`**: Path prefixes (e.g. `['/home', '/products', '/settings/branding']`).
- **`allowed_clicks`**: Buttons or links target text (e.g. `['Settings', 'Save Settings', 'Upload']`).

If `--no-llm` is passed or Ollama is offline, a heuristic backup runs to extract double-quoted terms (e.g., `"Settings"`) and capitalized phrases from steps and preconditions.

### 2. State-Signature based Deduplication
Dynamic applications may reload lists or trigger popups while staying on the same URL path. To prevent capturing redundant nodes:
1. Every interactive element's HTML tag, text, and locator is concatenated.
2. A unique MD5 hash is generated from this string.
3. If the hash matches an already visited state, the transition is logged, the duplicate folder is deleted, and the crawler redirects the link destination.

### 3. Playwright API Capturing
Under [Crawler/hooks.py], the `before_goto` hook binds a listener to Playwright's page request event:
```python
def handle_request(req):
    if req.resource_type in ["fetch", "xhr"]:
        captured_requests.append({"url": req.url, "method": req.method})
```
This logs both page-load APIs (fetch/xhr) and trigger action APIs (network traffic activated immediately following button clicks).

### 4. Redirect Isolation
When clicking buttons (e.g. `Logout`), pages might redirect to landing pages out of bounds. The crawler hooks inject a script checking for dynamic URL paths. If a redirection happens:
- A `redirected-url-marker` container is appended to the document body.
- The crawler captures the redirect, maps the transition edge, and terminates BFS branching for that node to prevent the session from breaking.
