import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status
from rich.theme import Theme

# Add root path to sys.path so we can import shared utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_utils.logger import get_logger
from Test_Case_Gen.utils.helpers import read_text_file
import Test_Case_Gen.generator as generator

# Load environment variables
load_dotenv()

# Initialize Logger
logger = get_logger("generator_main")

# Define custom styling theme for the terminal UI
custom_theme = Theme({
    "info": "bold cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "bold magenta",
})
console = Console(theme=custom_theme)

def display_banner():
    """Prints a beautiful title banner."""
    banner = (
        "+----------------------------------------------------------+\n"
        "|              T E S T C A S E - G E N                     |\n"
        "|    AI-Powered Local Test Case Generation Pipeline        |\n"
        "+----------------------------------------------------------+"
    )
    console.print(Panel(banner, style="highlight", expand=False))

def main():
    display_banner()
    
    # Parse CLI Arguments with environment variable defaults
    parser = argparse.ArgumentParser(
        description="Extract requirements and generate QA test cases from a requirements/prompt text file using local LLMs."
    )
    parser.add_argument("txt_path", help="Path to the prompt/requirements text (.txt) file")
    parser.add_argument(
        "--model", 
        default=os.getenv("OLLAMA_MODEL", "qwen3:8b"), 
        help=f"Ollama model to use (default: {os.getenv('OLLAMA_MODEL', 'qwen3:8b')})"
    )
    parser.add_argument(
        "--url", 
        default=os.getenv("OLLAMA_URL", "http://localhost:11434"), 
        help=f"Ollama API base URL (default: {os.getenv('OLLAMA_URL', 'http://localhost:11434')})"
    )
    parser.add_argument(
        "--output", 
        default=os.getenv("OUTPUT_DIR", "./output"), 
        help=f"Output folder path (default: {os.getenv('OUTPUT_DIR', './output')})"
    )
    args = parser.parse_args()
    
    txt_path = args.txt_path
    model = args.model
    ollama_url = args.url
    output_dir = os.path.abspath(args.output)
    
    # 1. Validate TXT exists and has correct extension
    if not os.path.isfile(txt_path):
        logger.error(f"Error: Text file not found at '{txt_path}'")
        console.print(f"[error]Error:[/] Text file not found at '{txt_path}'", style="error")
        sys.exit(1)
        
    if not txt_path.lower().endswith('.txt'):
        logger.error(f"Error: Invalid file format. Only '.txt' files are accepted. File was '{txt_path}'")
        console.print(f"[error]Error:[/] Invalid file format. Only '.txt' files are accepted.", style="error")
        sys.exit(1)
        
    logger.info(f"Source Text File: {txt_path}")
    logger.info(f"Ollama Model: {model}")
    logger.info(f"Ollama URL: {ollama_url}")
    logger.info(f"Output Folder: {output_dir}")
    
    console.print(f"[info]Source Text File:[/] {txt_path}")
    console.print(f"[info]Ollama Model:[/] {model}")
    console.print(f"[info]Ollama URL:[/] {ollama_url}")
    console.print(f"[info]Output Folder:[/] {output_dir}\n")
    
    # 2. Read text from file
    try:
        with Status("[info]Reading prompt from text file...[/]", console=console, spinner="dots") as status:
            brd_text = read_text_file(txt_path)
            char_count = len(brd_text)
            status.update("[success]Text file read successfully![/]")
        logger.info(f"Read {char_count} characters of text from file.")
        console.print(f"[success][OK][/] Read {char_count} characters of text from file.")
    except Exception as e:
        logger.error(f"Error reading text file: {e}")
        console.print(f"[error]Error reading text file:[/] {str(e)}")
        sys.exit(1)
        
    if not brd_text.strip():
        logger.warning("Warning: Text file content is empty. Please check the file contents.")
        console.print("[warning]Warning:[/] Text file content is empty. Please check the file contents.")
        sys.exit(1)
        
    try:
        # Step 1: AI Test Case Generation
        logger.info("Starting AI Test Case Generation pipeline...")
        console.print("\n[highlight]Starting AI Test Case Generation...[/]")
        with Status("[cyan]Analyzing specification text and generating exhaustive test cases (positive, negative, boundary, validations, security)... (this may take a moment)[/]", console=console, spinner="dots") as status:
            testcase_data = generator.generate_test_cases(brd_text, model, ollama_url, output_dir)
            tc_count = len(testcase_data.get("test_cases", []))
            status.update("[success]Generation complete![/]")
        
        logger.info(f"Generated {tc_count} test cases. Saved outputs to output/test_cases.json")
        console.print(f"[success][OK][/] Generated [bold]{tc_count}[/] test cases with mapped requirements. Saved to output/test_cases.json")
        
        # 3. Print final report and table
        console.print("\n" + "-" * 60)
        console.print("[success]>> Test Case Generation Pipeline Completed Successfully![/]\n")
        
        # Stats Table
        table = Table(title="Pipeline Output Summary", show_header=True, header_style="bold magenta")
        table.add_column("Pipeline Step", style="cyan")
        table.add_column("Items Count", justify="right", style="green")
        table.add_column("JSON Output Path", style="dim")
        
        table.add_row(
            "Test Case Generation", 
            str(tc_count), 
            os.path.join(args.output, "test_cases.json")
        )
        
        console.print(table)
        console.print("\n[info]All outputs are ready in the output directory![/]")
        
    except ConnectionError as e:
        logger.error(f"Connection Error: {e}")
        console.print(f"\n[error]Connection Error:[/] {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user. Exiting gracefully...")
        console.print("\n[warning]Process interrupted by user. Exiting gracefully...[/]")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")
        console.print(f"\n[error]Pipeline Failed:[/] {str(e)}")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)

if __name__ == "__main__":
    main()
