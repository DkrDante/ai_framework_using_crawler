#!/usr/bin/env bash
# ===========================================================================
# run_tests.sh — Cross-platform test runner for macOS / Linux
#
# Usage:
#   ./run_tests.sh                    # Run all tests (parallel)
#   ./run_tests.sh --smoke            # Run only smoke tests
#   ./run_tests.sh --regression       # Run full regression suite
#   ./run_tests.sh --api              # Run only API tests
#   ./run_tests.sh --ui               # Run only UI tests
#   ./run_tests.sh --tags "tag_expr"  # Run tests matching tag expression
# ===========================================================================

set -euo pipefail

MODE="${1:-all}"
TAG_EXPR="${2:-}"

# Clean old reports
echo "🧹 Cleaning old reports..."
rm -rf reports/* allure-report/

case "$MODE" in
    --smoke)
        echo "💨 Running smoke tests..."
        pytest -m smoke --alluredir=reports/
        allure serve reports
        ;;
    --regression)
        echo "🔁 Running full regression suite..."
        pytest -m "smoke or regression" --alluredir=reports/
        allure serve reports
        ;;
    --api)
        echo "🔌 Running API tests only..."
        pytest tests/api/ --alluredir=reports/
        allure serve reports
        ;;
    --ui)
        echo "🖥️  Running UI tests only..."
        pytest tests/ui/ --alluredir=reports/
        allure serve reports/
        ;;
    --tags)
        if [ -z "$TAG_EXPR" ]; then
            echo "❌ Error: --tags requires a tag expression (e.g. 'smoke and not ui')"
            exit 1
        fi
        echo "🏷️  Running tests with tags: $TAG_EXPR..."
        pytest -m "$TAG_EXPR" --alluredir=reports/
        allure serve reports
        ;;
    all|*)
        echo "▶️  Running all tests..."
        pytest --alluredir=reports/
        allure serve reports
        ;;
esac

# Generate and open Allure report
echo "📊 Generating Allure report..."
allure generate reports/ -o allure-report --clean
allure open allure-report
