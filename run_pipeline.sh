#!/bin/bash
# End-to-End Local QA Generation & Crawling Pipeline
# Exit script on any command failure
set -e

# Parse options
FRAMEWORK_ONLY=false
SKIP_REPORT=false
for arg in "$@"; do
  if [ "$arg" = "--framework-only" ] || [ "$arg" = "-f" ]; then
    FRAMEWORK_ONLY=true
  fi
  if [ "$arg" = "--skip-report" ]; then
    SKIP_REPORT=true
  fi
done

if [ "$FRAMEWORK_ONLY" = true ]; then
  echo "=========================================================="
  echo " Running Automation Framework Alone"
  echo "=========================================================="
  if [ -d "venv" ]; then
    echo "[Venv] Activating virtual environment..."
    source venv/Scripts/activate || source venv/bin/activate
  fi
  echo "[Step 1/1] Running Automation Framework tests..."
  pytest automation-framework/
  exit 0
fi

echo "=========================================================="
echo " Starting Local QA Automation Pipeline"
echo "=========================================================="

# 1. Activate virtual environment if present
if [ -d "venv" ]; then
  echo "[Venv] Activating virtual environment..."

  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
  elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
  else
    echo "No virtual environment activation script found."
    exit 1
  fi
fi

# 2. Run Test Case Generator
echo ""
echo "[Step 1] Running AI Test Case Generator..."
python Test_Case_Gen/main.py Test_Case_Gen/brd_prompt.txt

# 3. Run guided Crawler
echo ""
echo "[Step 2] Running Test-Case Guided Crawler..."
python Crawler/crawl_graph.py --test-cases output/test_cases.json

# 4. Run Code Generator (test_cases.json → pytest files)
echo ""
echo "[Step 3] Running AI Code Generator (test cases → pytest files)..."
python Code_Gen/main.py \
  --test-cases output/test_cases.json \
  --output-dir output \
  --framework-tests-dir automation-framework/tests/ai_generated

# 5. Run Automation Framework
echo ""
echo "[Step 4] Running Automation Framework tests..."
pytest automation-framework/

# 5. Generate & open Allure report
echo ""
echo "[Step 5] Generating Allure HTML Report..."

if command -v allure &> /dev/null; then
  # Compile raw JSON results → HTML report (--clean wipes stale data)
  allure generate reports \
    --output allure-report \
    --clean \
    --single-file 2>/dev/null || true

  REPORT_PATH="allure-report/index.html"
  if [ -f "$REPORT_PATH" ]; then
    echo "[OK] Allure report generated at: $(pwd)/$REPORT_PATH"
  fi

  if [ "$SKIP_REPORT" = false ]; then
    echo "[Info] Opening Allure report in browser..."
    allure open allure-report 2>/dev/null &
  else
    echo "[Info] Skipping report browser open (--skip-report flag set)."
    echo "       To view: allure open allure-report"
  fi
else
  echo "[Warning] Allure CLI not found. Skipping report generation."
  echo "          Install with: brew install allure"
fi

