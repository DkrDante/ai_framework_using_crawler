param(
    [string]$Mode = "all"
)
Write-Host "=== SatoriXR Test Runner ==="

# Clean old reports
Write-Host "Cleaning old reports..."
if (Test-Path "reports") {
    Remove-Item reports\* -Recurse -Force
} else {
    New-Item -ItemType Directory -Path reports | Out-Null
}

if (Test-Path "allure-report") {
    Remove-Item allure-report -Recurse -Force
}

switch ($Mode) {
    "parallel" {
        Write-Host "Running all tests (API and UI) in parallel..."
        pytest -n auto --alluredir=reports/
    }
    "smoke" {
        Write-Host "Running smoke tests..."
        pytest -m smoke --alluredir=reports/
    }
    "regression" {
        Write-Host "Running full regression suite..."
        pytest -m "smoke or regression" --alluredir=reports/
    }
    "api" {
        Write-Host "Running API tests only..."
        pytest tests/api/ --alluredir=reports/
    }
    "ui" {
        Write-Host "Running UI tests only..."
        pytest tests/ui/ --alluredir=reports/
    }
    default {
        Write-Host "Running all tests..."
        pytest --alluredir=reports/
    }
}

Write-Host "Generating Allure report..."
allure generate reports/ -o allure-report --clean
allure open allure-report