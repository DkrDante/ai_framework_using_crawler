@echo off
rem End-to-End Local QA Generation & Crawling Pipeline for Windows CMD
rem Check if framework-only is requested
set FRAMEWORK_ONLY=false
if "%~1"=="--framework-only" set FRAMEWORK_ONLY=true
if "%~1"=="-f" set FRAMEWORK_ONLY=true

if "%FRAMEWORK_ONLY%"=="true" (
    echo ==========================================================
    echo  Running Automation Framework Alone
    echo ==========================================================
    if exist venv\Scripts\activate.bat (
        echo [Venv] Activating virtual environment...
        call venv\Scripts\activate.bat
    )
    echo [Step 1/1] Running Automation Framework tests...
    pytest automation-framework\
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Automation Framework tests failed!
        exit /b %ERRORLEVEL%
    )
    exit /b 0
)

echo ==========================================================
echo  Starting Local QA Automation Pipeline
echo ==========================================================

rem 1. Activate virtual environment if present
if exist venv\Scripts\activate.bat (
    echo [Venv] Activating virtual environment...
    call venv\Scripts\activate.bat
)

rem 2. Run Test Case Generator
echo.
echo [Step 1] Running AI Test Case Generator...
python Test_Case_Gen\main.py Test_Case_Gen\test_promt.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Test Case Generation failed!
    exit /b %ERRORLEVEL%
)

rem 3. Run guided Crawler
echo.
echo [Step 2] Running Test-Case Guided Crawler...
python Crawler\crawl_graph.py --test-cases output\test_cases.json
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Guided Crawler failed!
    exit /b %ERRORLEVEL%
)

rem 4. Run Automation Framework
echo.
echo [Step 3] Running Automation Framework tests...
pytest automation-framework\
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Automation Framework tests failed!
    exit /b %ERRORLEVEL%
)


echo.
echo ==========================================================
echo  Pipeline Execution Completed Successfully!
echo ==========================================================
