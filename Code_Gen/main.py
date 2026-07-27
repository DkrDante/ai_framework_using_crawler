"""
Code Generator — CLI Entry Point

Reads output/test_cases.json + crawled output/*/elements.json,
calls a local Ollama LLM to synthesize pytest + Playwright test code,
validates it, and writes it to automation-framework/tests/ai_generated/.

Usage:
    python Code_Gen/main.py [--test-cases <path>] [--model <model>] [--url <ollama_url>]
"""

import os
import sys
import argparse

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status
from rich.theme import Theme

# Allow imports from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_utils.logger import get_logger
import Code_Gen.generator as generator

load_dotenv()

logger = get_logger("code_gen_main")

custom_theme = Theme({
    "info":      "bold cyan",
    "warning":   "bold yellow",
    "error":     "bold red",
    "success":   "bold green",
    "highlight": "bold magenta",
})
console = Console(theme=custom_theme)


def display_banner():
    banner = (
        "+----------------------------------------------------------+\n"
        "|              C O D E - G E N                             |\n"
        "|   AI-Powered Pytest Code Generation from Test Cases      |\n"
        "+----------------------------------------------------------+"
    )
    console.print(Panel(banner, style="highlight", expand=False))


def main():
    display_banner()

    parser = argparse.ArgumentParser(
        description="Generate pytest + Playwright test code from test_cases.json using a local LLM."
    )
    parser.add_argument(
        "--test-cases",
        default=os.getenv("TEST_CASES_PATH", "./output/test_cases.json"),
        help="Path to the test_cases.json file (default: ./output/test_cases.json)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("OUTPUT_DIR", "./output"),
        help="Crawler output directory containing page element snapshots (default: ./output)",
    )
    parser.add_argument(
        "--framework-tests-dir",
        default=os.getenv(
            "FRAMEWORK_TESTS_DIR",
            "./automation-framework/tests/ai_generated",
        ),
        help="Destination directory for generated test files (default: ./automation-framework/tests/ai_generated)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        help=f"Ollama model to use (default: {os.getenv('OLLAMA_MODEL', 'qwen3:8b')})",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        help=f"Ollama API base URL (default: {os.getenv('OLLAMA_URL', 'http://localhost:11434')})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Number of retry attempts if the generated code has syntax errors (default: 2)",
    )
    args = parser.parse_args()

    test_cases_path   = os.path.abspath(args.test_cases)
    output_dir        = os.path.abspath(args.output_dir)
    framework_dir     = os.path.abspath(args.framework_tests_dir)
    model             = args.model
    ollama_url        = args.url

    console.print(f"[info]Test Cases File:[/]       {test_cases_path}")
    console.print(f"[info]Crawler Output Dir:[/]    {output_dir}")
    console.print(f"[info]Framework Tests Dir:[/]   {framework_dir}")
    console.print(f"[info]Ollama Model:[/]           {model}")
    console.print(f"[info]Ollama URL:[/]             {ollama_url}\n")

    # Validate test cases file exists
    if not os.path.isfile(test_cases_path):
        console.print(f"[error]Error:[/] test_cases.json not found at '{test_cases_path}'")
        sys.exit(1)

    try:
        with Status(
            "[cyan]Generating pytest test code from test cases (this may take a minute)...[/]",
            console=console,
            spinner="dots",
        ) as status:
            results = generator.generate_test_code(
                test_cases_path=test_cases_path,
                output_dir=output_dir,
                framework_tests_dir=framework_dir,
                model=model,
                ollama_url=ollama_url,
                max_retries=args.retries,
            )
            status.update("[success]Code generation complete![/]")

        if not results:
            console.print("[warning]No test files were generated. Check logs for errors.[/]")
            sys.exit(1)

        # Summary table
        console.print("\n" + "-" * 60)
        console.print("[success]>> Code Generation Completed Successfully!\n[/]")

        table = Table(title="AI Test File Diff Summary", show_header=True, header_style="bold magenta")
        table.add_column("File",        style="cyan")
        table.add_column("Action",      style="bold")
        table.add_column("Added",       justify="right", style="green")
        table.add_column("Retained",    justify="right", style="dim")
        table.add_column("Deleted",     justify="right", style="red")

        for r in results:
            action_color = {
                "created":   "[green]created[/]",
                "updated":   "[yellow]updated[/]",
                "unchanged": "[dim]unchanged[/]",
            }.get(r.action, r.action)
            table.add_row(
                os.path.basename(r.file),
                action_color,
                str(len(r.added)),
                str(len(r.retained)),
                str(len(r.deleted)),
            )

        console.print(table)
        console.print(f"\n[info]Files saved to:[/] {framework_dir}")
        console.print("[info]Run them with:[/] pytest automation-framework/tests/ai_generated/\n")

    except ConnectionError as exc:
        console.print(f"\n[error]Connection Error:[/] {exc}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[warning]Interrupted by user.[/]")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Code generation failed: {exc}")
        console.print(f"\n[error]Pipeline Failed:[/] {exc}")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


if __name__ == "__main__":
    main()
