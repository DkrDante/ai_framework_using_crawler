#!/bin/bash
# =============================================================================
#  SatoriXR — AI-Powered QA Demo Runner
#  Runs the complete test suite and opens the Allure report in your browser.
#
#  Usage:
#    ./demo_run.sh              → full run (all 91 tests + allure)
#    ./demo_run.sh --smoke      → only smoke tests (fastest, ~12 tests)
#    ./demo_run.sh --no-open    → run + generate report but don't open browser
# =============================================================================

set -e

# ── Parse flags ──────────────────────────────────────────────────────────────
SMOKE_ONLY=false
OPEN_REPORT=true
for arg in "$@"; do
  [ "$arg" = "--smoke" ]    && SMOKE_ONLY=true
  [ "$arg" = "--no-open" ]  && OPEN_REPORT=false
done

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║          SatoriXR  ·  AI-Powered QA Automation              ║"
echo "  ║        End-to-End Test Suite  ·  Live Demo Run              ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  ${YELLOW}Started:${RESET}  $(date '+%A %d %B %Y  %H:%M:%S')"
echo ""

# ── Activate virtual environment ──────────────────────────────────────────────
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
else
  echo -e "  ${RED}✖  No virtual environment found. Run: python3 -m venv venv && pip install -r requirements.txt${RESET}"
  exit 1
fi

# ── Pre-run cleanup ───────────────────────────────────────────────────────────
echo -e "  ${CYAN}⟳  Preparing clean run environment...${RESET}"

# Clear old allure results so the report only shows today's run
rm -rf reports/ allure-report/ 2>/dev/null || true
mkdir -p reports

# Remove stale login failure flag (safe to delete — re-login will happen if needed)
rm -f .auth/login_failed.txt 2>/dev/null || true

echo -e "  ${GREEN}✔  Clean slate ready${RESET}"
echo ""

# ── Determine test selection ───────────────────────────────────────────────────
if [ "$SMOKE_ONLY" = true ]; then
  MARKS="-m smoke"
  LABEL="Smoke Tests Only (fastest path)"
else
  MARKS=""
  LABEL="Full Test Suite (AI + UI + API)"
fi

echo -e "  ${BOLD}▶  Running: ${LABEL}${RESET}"
echo -e "  ${YELLOW}   Workers: 6 parallel  ·  Retries: 1  ·  Browser: Chromium${RESET}"
echo ""
echo "  ────────────────────────────────────────────────────────────────"
echo ""

# ── Run tests ─────────────────────────────────────────────────────────────────
START_TIME=$SECONDS

set +e   # Don't exit on test failures — we still want the report
pytest automation-framework/ \
  $MARKS \
  --tb=short \
  --no-header \
  -p no:randomly \
  --screenshot on \
  --video retain-on-failure \
  --tracing retain-on-failure \
  --alluredir=reports \
  -n 6 \
  --dist loadfile \
  --reruns 1 \
  --reruns-delay 3
EXIT_CODE=$?
set -e

ELAPSED=$(( SECONDS - START_TIME ))
MINS=$(( ELAPSED / 60 ))
SECS=$(( ELAPSED % 60 ))

echo ""
echo "  ────────────────────────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Run completed in ${MINS}m ${SECS}s${RESET}"
echo ""

# ── Generate Allure report ────────────────────────────────────────────────────
echo -e "  ${CYAN}⟳  Generating Allure HTML report...${RESET}"

if command -v allure &>/dev/null; then
  allure generate reports \
    --output allure-report \
    --clean \
    --single-file 2>/dev/null || true

  if [ -f "allure-report/index.html" ]; then
    echo -e "  ${GREEN}✔  Report generated: $(pwd)/allure-report/index.html${RESET}"
  fi

  if [ "$OPEN_REPORT" = true ]; then
    echo ""
    echo -e "  ${BOLD}${CYAN}↗  Opening Allure report in your browser...${RESET}"
    # allure open serves on a local port and opens the browser
    allure open allure-report 2>/dev/null &
  else
    echo ""
    echo -e "  ${YELLOW}ℹ  To view the report: allure open allure-report${RESET}"
  fi
else
  echo -e "  ${YELLOW}⚠  Allure CLI not found. Install with: brew install allure${RESET}"
  echo -e "     Then run: allure generate reports --output allure-report --clean"
fi

# ── Final summary ─────────────────────────────────────────────────────────────
echo ""
echo "  ────────────────────────────────────────────────────────────────"
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}  ✔  ALL TESTS PASSED${RESET}"
else
  echo -e "  ${RED}${BOLD}  ✖  SOME TESTS FAILED  (exit code $EXIT_CODE)${RESET}"
  echo -e "  ${YELLOW}     See the Allure report for screenshots and full details.${RESET}"
fi
echo "  ────────────────────────────────────────────────────────────────"
echo ""

exit $EXIT_CODE
