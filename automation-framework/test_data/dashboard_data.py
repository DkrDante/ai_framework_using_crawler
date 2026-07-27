import json
import re
from pathlib import Path

# Load JSON data
_data_file = Path(__file__).parent / "dashboard_data.json"
with open(_data_file, "r") as f:
    _data = json.load(f)

DASHBOARD_URL_PATTERN = re.compile(_data["dashboard_url_pattern"])
OVERVIEW_HEADING = _data["overview_heading"]
EXPECTED_CARDS = _data["expected_cards"]
EXPECTED_NAV_ITEMS = _data["expected_nav_items"]
EXPECTED_SUB_NAV_ITEMS = _data["expected_sub_nav_items"]
