# Automation Framework

This repository contains an automated testing framework built with Python, Pytest, Playwright, and Requests. It supports both UI and API testing and provides comprehensive test reporting using Allure.

## Features

- **UI Testing**: Powered by [Playwright](https://playwright.dev/python/) for fast, reliable, and cross-browser web testing.
- **API Testing**: Uses Playwright's API request context for authenticated RESTful API testing.
- **Reporting**: Integrates directly with [Allure Framework](https://allurereport.org/) for beautiful, detailed test reports.
- **Configuration**: Uses YAML files (`config/config.yaml`) + `.env` for clean and structured environment configurations.
- **Page Object Model (POM)**: All UI interaction is encapsulated in `pages/` — locators and actions only, no assertions.
- **Service Layer**: API calls are wrapped in `services/` to keep tests focused on validation.
- **Reusable Fixtures**: Authentication, API context, reporting, and config are managed via modular fixtures in `fixtures/`.

## Directory Structure

```text
automation-framework/
├── config/                    # Environment configuration (YAML + .env)
│   ├── __init__.py
│   └── config.yaml
├── fixtures/                  # Reusable pytest fixtures (modular)
│   ├── __init__.py
│   ├── api_fixtures.py        # Authenticated API request context
│   ├── auth_fixtures.py       # Session-scoped login & storage state
│   ├── config_fixtures.py     # YAML + env config loader
│   └── reporting_fixtures.py  # Allure screenshot/video on failure
├── pages/                     # Page Object Model classes (locators + actions ONLY)
│   ├── __init__.py
│   ├── base_page.py           # Common actions shared by all pages
│   ├── dashboard_page.py      # Dashboard-specific locators & helpers
│   └── login_page.py          # Login flow locators & actions
├── services/                  # Business-logic wrappers (API clients, etc.)
│   ├── __init__.py
│   ├── base_api_service.py    # Common API error and base service wrappers
│   ├── dashboard_api_service.py  # DashboardAPIService — wraps dashboard API calls
│   ├── user_management_api_service.py # UserManagementAPIService — wraps user management API calls
│   └── branding_api_service.py  # BrandingAPIService — wraps branding API calls
├── test_data/                 # Constants & data-driven test inputs
│   ├── __init__.py
│   └── dashboard_data.py      # URL patterns, card titles, nav items
├── tests/                     # All test execution scripts
│   ├── __init__.py
│   ├── api/                   # API-only tests
│   │   ├── __init__.py
│   │   └── test_dashboard_api.py
│   └── ui/                    # UI (browser) tests
│       ├── __init__.py
│       └── test_dashboard_ui.py
├── utils/                     # Utility and helper functions
│   ├── __init__.py
│   ├── email_otp.py           # IMAP-based OTP fetcher
│   └── waits.py               # Reusable wait strategies
├── .gitignore
├── conftest.py                # Pytest entrypoint — registers fixture plugins
├── pytest.ini                 # Pytest configuration & custom markers
├── requirements.txt           # Python dependencies
└── run_tests.ps1              # PowerShell script to execute tests and open reports
```

## Architecture Principles

| Principle | Implementation |
|-----------|---------------|
| **Separation of concerns** | `tests/` → assertions only · `pages/` → locators + actions · `services/` → API wrappers · `fixtures/` → setup/teardown |
| **No assertions in Page Objects** | Pages return locators/values; tests make the assertions |
| **DRY test data** | All constants live in `test_data/` — tests import, never hardcode |
| **Service layer** | Page-specific API Services centralise HTTP calls; tests validate responses |
| **Smart fallback locators** | `DashboardPage.get_metric_card()` auto-falls-back when primary selector misses |

## Prerequisites

1. **Python 3.10+** installed on your system.
2. **Pip** (Python package installer).
3. **Allure Commandline** installed and added to your system path.

## Setup Instructions

1. **Create and Activate a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   # .\venv\Scripts\activate       # Windows PowerShell
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**
   ```bash
   playwright install
   ```

4. **Environment Variables**
   Create a `.env` file in the project root:
   ```env
   EMAIL_USER=your-email@example.com
   EMAIL_PASS=your-email-password
   ```

## Running Tests

### All tests (sequential)
```bash
pytest
```

### Parallel execution (UI & API tests)
```bash
pytest -n auto                       # auto-detect CPU cores for all tests
pytest tests/ui/ -n 4                # run UI tests with 4 parallel workers
```

> **Note:** Both UI and API tests are fully parallelizable! The framework leverages an atomic lock-based synchronization system to log in once and share the authenticated browser state securely across parallel workers without conflicts.

### Tag-based execution
```bash
pytest -m smoke                    # quick CI gate (~30s)
pytest -m regression               # detailed schema checks
pytest -m "smoke or regression"    # full suite
pytest -m ui                       # all UI tests
pytest -m api                      # all API tests
pytest -m "ui and smoke"           # only UI smoke tests
```

| Marker | Purpose | Tests |
|--------|---------|-------|
| `smoke` | Fast sanity — blocks deploys if broken | Key endpoint + page checks |
| `regression` | Full schema validation | Every field-level assertion |
| `ui` | All browser tests | Dashboard UI + Login |
| `api` | All HTTP tests | Auth, Stats, Products, Scenes |
| `flaky` | Known unstable tests | Auto-retried |

### Retry mechanism
Failed tests are automatically retried **2 times** with a **3-second delay** (configured in `pytest.ini`). Override via CLI:
```bash
pytest --reruns 3 --reruns-delay 5   # 3 retries, 5s delay
pytest --reruns 0                    # disable retries
```

### With Allure report
```bash
pytest --alluredir=reports/
allure serve reports/
```

### Using the helper scripts

```bash
# macOS / Linux
./run_tests.sh                     # all tests
./run_tests.sh --parallel          # API parallel + UI sequential
./run_tests.sh --smoke             # smoke only
./run_tests.sh --regression        # full regression
./run_tests.sh --api               # API only
./run_tests.sh --ui                # UI only
```

```powershell
# Windows
.\run_tests.ps1                    # all tests
.\run_tests.ps1 -Mode parallel     # API parallel + UI sequential
.\run_tests.ps1 -Mode smoke        # smoke only
```

## Performance Optimizations

| Optimization | How |
|-------------|-----|
| **Login once per session** | `global_auth_state` fixture (session-scoped) logs in once, saves storage state |
| **Shared API context** | `api_context` is session-scoped — one authenticated context for all API tests |
| **Module-scoped API responses** | `token_response`, `stats_response`, etc. fetch once per module, shared across tests |
| **Parallel API tests** | `pytest-xdist` runs API tests across CPU cores (`-n auto`) |
| **Auto-retry flaky tests** | `pytest-rerunfailures` avoids false negatives from network hiccups |

## Writing Tests

- **UI Tests**: Add to `tests/ui/`. Use page objects from `pages/` and data from `test_data/`. Never put raw locators in test files. Tag with `@pytest.mark.ui`.
- **API Tests**: Add to `tests/api/`. Create service methods in `services/<feature>_api_service.py` for new endpoints; tests call services and assert. Tag with `@pytest.mark.api`.
- **New Pages**: Inherit from `BasePage`. Keep only locators and actions — no assertions.
- **Markers**: Always tag tests with `smoke` or `regression` for filtering support.

## Debugging Failures & Visual Evidence

The framework automatically captures visual evidence upon test failures or setup errors and attaches them directly to the Allure report. This works seamlessly in both sequential and parallel execution modes:

- **Automated Screenshots (Photos)**: Captured for any failed test step or setup error to show the exact visual state of the application.
- **Automated Video Recordings**: Recorded for UI test runs and automatically flushed, verified, and attached as `.webm` files when a test fails.
- **Trace Files**: Playwright trace files can be inspected for deep execution timelines:
  ```bash
  playwright show-trace test-results/<trace-zip-file>
  ```
