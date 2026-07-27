import asyncio
import os
import sys
import json
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv

# Add root path to sys.path so we can import shared utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_utils.logger import get_logger
from Crawler.login_manager import ensure_login_state
from Crawler.constraint_extractor import load_test_cases_constraints
from Crawler.process_worker import worker

# Reconfigure stdout/stderr to UTF-8 to prevent encoding errors on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Logger initialization
logger = get_logger("crawler")

script_dir = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.abspath(os.path.join(script_dir, "..", ".auth", "state.json"))

# Test Case Guided Crawling Constraints
ALLOWED_CLICKS = None
ALLOWED_URLS = None

# Global configuration
CONFIG = {
    'start_url': '',
    'output_dir': 'output',
    'width': 1920,
    'height': 1080,
    'concurrency': 3,
    'max_depth': 1
}

url_to_folder = {}
visited_signatures = {} # MD5 -> State URL
visited_states = set()
graph_pages = []
graph_links = []
graph_lock = asyncio.Lock() # For writing to graph safely

async def main():
    parser = argparse.ArgumentParser(description="Asynchronous crawling and dynamic graph construction using crawl4ai.")
    parser.add_argument("--url", default="https://try.satorixr.com/home", help="Target URL to start crawling")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--concurrency", type=int, default=3, help="Max parallel crawler instances")
    parser.add_argument("--max-depth", type=int, default=1, help="Max click interaction depth")
    parser.add_argument("--test-cases", default="output/test_cases.json", help="Path to the test cases JSON file to guide/constrain the crawl")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable Ollama LLM guidance and pruning")
    parser.set_defaults(use_llm=True)
    parser.add_argument("--api-only", action="store_true", help="Only run API capture and skip visual screenshots/graphs")
    args = parser.parse_args()

    # Load constraints strictly
    global ALLOWED_CLICKS, ALLOWED_URLS
    try:
        ALLOWED_CLICKS, ALLOWED_URLS = load_test_cases_constraints(args.test_cases)
    except Exception as e:
        logger.error(f"\n[CRITICAL ERROR] Failed to load test case constraints: {e}\n")
        sys.exit(1)

    # Initialize/verify login state
    try:
        await ensure_login_state(STATE_PATH)
    except Exception as e:
        logger.error(f"\n[CRITICAL ERROR] Failed to initialize login state: {e}\n")
        sys.exit(1)

    # Configure global settings
    CONFIG['start_url'] = args.url
    CONFIG['output_dir'] = args.output
    CONFIG['concurrency'] = args.concurrency
    CONFIG['max_depth'] = args.max_depth
    CONFIG['use_llm'] = args.use_llm
    CONFIG['test_cases_path'] = args.test_cases
    CONFIG['api_only'] = args.api_only

    os.makedirs(args.output, exist_ok=True)
    parsed_start = urlparse(args.url)
    start_domain = parsed_start.netloc

    logger.info("=" * 60)
    logger.info(f"Starting parallel async crawl for: {args.url}")
    logger.info(f"Max Interaction click-depth: {args.max_depth}")
    logger.info(f"Concurrency level: {args.concurrency}")
    logger.info(f"Output folder: {args.output}")
    logger.info(f"Ollama LLM guidance: {'Enabled' if args.use_llm else 'Disabled'}")
    logger.info("=" * 60)

    # Extract unique URLs from test cases to seed the queue
    urls_from_json = set()
    try:
        with open(args.test_cases, "r", encoding="utf-8") as f:
            data = json.load(f)
            for tc in data.get("test_cases", []):
                if tc.get("url"):
                    urls_from_json.add(tc["url"])
    except Exception as e:
        logger.error(f"Error reading test cases for URL seeding: {e}")

    # Setup BFS queue with tuples (url, interaction_path, source_state_url, click_info)
    queue = asyncio.Queue()
    if urls_from_json:
        logger.info(f"[Crawler] Seeding queue with {len(urls_from_json)} unique URLs from test cases: {list(urls_from_json)}")
        for url in sorted(urls_from_json):
            visited_states.add(url)
            await queue.put((url, [], None, None))
    else:
        logger.info(f"[Crawler] No URLs found in test cases. Seeding with start URL: {args.url}")
        visited_states.add(args.url)
        await queue.put((args.url, [], None, None))

    # Spawn independent workers
    global_apis = {}
    workers = []
    for _ in range(args.concurrency):
        task = asyncio.create_task(worker(
            queue, start_domain, STATE_PATH, CONFIG, url_to_folder, visited_signatures,
            visited_states, graph_pages, graph_links, graph_lock, ALLOWED_CLICKS, ALLOWED_URLS,
            global_apis
        ))
        workers.append(task)

    # Wait for all items in the queue to be processed and completed
    await queue.join()

    # Cancel workers
    for task in workers:
        task.cancel()
    await asyncio.gather(*workers, return_exceptions=True)

    if not CONFIG.get('api_only'):
        # Generate final site_graph.json
        graph = {
            "start_url": args.url,
            "max_depth_limit": args.max_depth,
            "pages": graph_pages,
            "links": graph_links
        }
        
        graph_path = os.path.join(args.output, "site_graph.json")
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=4)

    # Generate final api.json (deduplicated)
    api_list = []
    for key, api_info in global_apis.items():
        api_list.append(api_info)

    api_path = os.path.join(args.output, "api.json")
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api_list, f, indent=4)

    logger.info("=" * 60)
    logger.info("Async crawl completed successfully!")
    logger.info(f"Total States Captured: {len(graph_pages)}")
    logger.info(f"Total Transitions/Edges Found: {len(graph_links)}")
    logger.info(f"Total Unique APIs Captured: {len(api_list)}")
    logger.info(f"Results saved to: {os.path.abspath(args.output)}")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
