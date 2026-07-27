# AI Test Case Generator (`Test_Case_Gen`)

This module uses local Large Language Models (LLMs) to automatically generate comprehensive QA test case suites from business requirements and specification texts. It parses functional requirements, structures them, and generates positive, negative, validation, boundary, and security test cases.

---

## File Structure & Module Map

- [main.py]: CLI entrypoint. Handles input arguments, validates extension checks (only `.txt` formats are accepted), starts Rich terminal spinners, handles runtime errors, and displays a summary table when finished.
- [generator.py]: Connection handler for the local Ollama services. Enforces JSON formatting payloads, configures temperature tolerances (default `0.2` for deterministic QA output) and context window extensions (`32768` to support complex requirement files).
- [constants/prompts.py]: System and user prompt declarations instructing the LLM on specific functional coverage rules (Positive, Negative, Boundary, Validation, Security).
- [utils/helpers.py]: File exporters and schemas. Corrects missing keys from raw outputs, generates multi-line string structures, and creates the formatted Excel workbook.
- Specification Inputs:
  - [brd_prompt.txt]: Base requirement document containing SatoriXR portal specs for Dashboard, Products list, Experiences cards, and menus.
  - [test_promt.txt]: Extended requirement document containing detailed specifications for the Settings modules, user management, and Branding customizations (company logos, color parameters).

---

## CLI Reference

Execute the test case generator from the repository root:
```bash
python Test_Case_Gen/main.py <path_to_txt_file> [options]
```

### Positional Arguments
- `<path_to_txt_file>`: Path to the plain text file (`.txt`) containing the business specification.

### Options

| Command Option | Default Value | Description |
| :--- | :--- | :--- |
| `--model <string>` | `qwen3:8b` (or `OLLAMA_MODEL` env) | Name of the local Ollama model to use. |
| `--url <string>` | `http://localhost:11434` (or `OLLAMA_URL` env) | Endpoint URL of the local Ollama server. |
| `--output <path>` | `./output` (or `OUTPUT_DIR` env) | Directory folder where the generated JSON/XLSX spreadsheets are saved. |

---

## Output Formats and Schema

The generator writes two output files: `test_cases.json` and `test_cases.xlsx`.

### 1. JSON Schema Structure
The raw output is validated against the following schema:
```json
{
  "test_cases": [
    {
      "id": "TC-001",
      "title": "Verify SatoriXR Admin Login",
      "priority": "High",
      "type": "Positive",
      "validation": [
        "UI",
        "API"
      ],
      "requirements": [
        "REQ-001: Authenticate administrators securely."
      ],
      "preconditions": [
        "Admin user account exists",
        "Browser session is unauthenticated"
      ],
      "steps": [
        "1. Enter email address in the field.",
        "2. Click the 'Send Verification Code' button.",
        "3. Enter the 6-digit verification code received in email.",
        "4. Click 'Verify & Sign In' button."
      ],
      "expected_result": "System authenticates admin user and redirects to dashboard."
    }
  ]
}
```

### 2. Beautified Excel Spreadsheet
The [utils/helpers.py] module formats the Excel file for stakeholders:
- **Wrap Text**: Enabled on all cells to support multi-line test steps and preconditions.
- **Top Alignment**: Prevents contents from overlapping vertically.
- **Auto-Fit Widths**: The exporter computes the maximum character length for each column and sets column widths dynamically.
- **Readable Lists**: Array structures (e.g. preconditions, steps) are converted to clean, vertical line lists inside cells.

---

## Core Technical Concepts

### Rich Terminal UI
The CLI is built using the `rich` console package:
- **Custom Theme**: Integrates dedicated color logs for info alerts (bold cyan), validation warnings (yellow), runtime errors (bold red), and completion steps (green).
- **Process Spinners**: Tracks the local LLM generation progress dynamically while displaying processing status messages.
- **Execution Table**: Renders a summary table containing stats on generated items, JSON paths, and Excel paths.
