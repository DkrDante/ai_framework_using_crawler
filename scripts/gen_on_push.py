#!/usr/bin/env python3
"""
gen_on_push.py
==============
Called by the pre-push git hook.

Workflow:
  1. Run `git diff` to get the list of changed Python files.
  2. Parse every modified/added function and class from those files using the AST.
  3. Build a feature-description prompt from the extracted signatures + docstrings.
  4. Write the prompt to output/push_prompt_<timestamp>.txt.
  5. Invoke Test_Case_Gen/main.py with that prompt file.
  6. Exit 0 (push continues) or 1 (push blocked) based on HOOK_BLOCKING env var.
"""

import os
import sys
import ast
import json
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
# Resolve project root (one level up from scripts/)
# ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Allow importing shared_utils / Test_Case_Gen from anywhere
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv optional here; env vars can be set externally

# ──────────────────────────────────────────────
# Config from env
# ──────────────────────────────────────────────
HOOK_BLOCKING   = os.getenv("HOOK_BLOCKING", "true").lower() in ("1", "true", "yes")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_URL      = os.getenv("OLLAMA_URL", "http://localhost:11434")
OUTPUT_DIR      = Path(os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "output")))
VENV_PYTHON     = PROJECT_ROOT / "venv" / "bin" / "python"

# Fallback: use system python if venv doesn't exist
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "ℹ", "OK": "✅", "WARN": "⚠️ ", "ERROR": "❌"}.get(level, "•")
    print(f"  [{prefix}] {msg}", flush=True)


def get_changed_python_files(repo_root: Path) -> list[Path]:
    """Return .py files that changed between HEAD~1 and HEAD (staged + committed)."""
    try:
        # Try HEAD~1..HEAD (at least one prior commit exists)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", "HEAD~1", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=True
        )
        files = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        # First commit — diff against empty tree
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM",
             "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "HEAD"],
            cwd=repo_root, capture_output=True, text=True
        )
        files = result.stdout.strip().splitlines()

    py_files = [repo_root / f for f in files if f.endswith(".py")]
    return [f for f in py_files if f.exists()]


def _get_top_level_functions(tree: ast.Module) -> set:
    """Return the set of top-level function/async-function nodes (direct children of Module)."""
    top = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top.add(node)
    return top


def extract_features_from_file(filepath: Path) -> list[dict]:
    """
    Parse a Python file with AST and extract:
      - Module-level docstring (if any)
      - Classes: name + docstring + method signatures
      - Top-level functions: name + docstring + args
    Returns a list of feature dicts.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return [{"type": "file", "name": str(filepath.name), "description": "(could not parse file)"}]

    features = []

    # Module docstring
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        features.append({"type": "module", "name": filepath.name, "description": mod_doc})

    top_level_funcs = _get_top_level_functions(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    doc = ast.get_docstring(item) or ""
                    methods.append({
                        "name": item.name,
                        "args": args,
                        "docstring": doc[:300] if doc else ""
                    })
            features.append({
                "type": "class",
                "name": node.name,
                "file": filepath.name,
                "docstring": (ast.get_docstring(node) or "")[:400],
                "methods": methods
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node in top_level_funcs:
                args = [a.arg for a in node.args.args]
                doc = ast.get_docstring(node) or ""
                features.append({
                    "type": "function",
                    "name": node.name,
                    "file": filepath.name,
                    "args": args,
                    "docstring": doc[:400]
                })

    return features


def build_prompt(changed_files: list[Path], repo_root: Path) -> str:
    """
    Build a rich, LLM-ready feature specification from changed Python files.
    The result is injected into the Test_Case_Gen prompt template as {txt_content}.
    """
    lines = [
        "## Automated Push-Triggered Test Case Generation",
        "",
        "The following features were modified or added in the latest git push.",
        "Generate exhaustive positive QA test cases for each feature listed below.",
        "",
        "---",
    ]

    for filepath in changed_files:
        rel = filepath.relative_to(repo_root)
        lines.append(f"\n## Changed File: `{rel}`\n")
        features = extract_features_from_file(filepath)

        if not features:
            lines.append("_(no extractable features — file may be configuration or data)_\n")
            continue

        for feat in features:
            ftype = feat.get("type", "")

            if ftype == "module":
                lines.append(f"**Module description:** {feat['description']}\n")

            elif ftype == "class":
                lines.append(f"### Class: `{feat['name']}`")
                if feat.get("docstring"):
                    lines.append(f"> {feat['docstring']}")
                for m in feat.get("methods", []):
                    sig = f"`{m['name']}({', '.join(m['args'])})`"
                    lines.append(f"- Method {sig}")
                    if m.get("docstring"):
                        lines.append(f"  - {m['docstring']}")
                lines.append("")

            elif ftype == "function":
                sig = f"`{feat['name']}({', '.join(feat.get('args', []))})`"
                lines.append(f"### Function: {sig}")
                if feat.get("docstring"):
                    lines.append(f"> {feat['docstring']}")
                lines.append("")

    lines += [
        "---",
        "",
        "Generate test cases covering all the above features.",
        "Focus on: happy paths, edge cases, input validation, and UI/API interactions.",
    ]
    return "\n".join(lines)


def save_prompt(prompt_text: str, timestamp: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = OUTPUT_DIR / f"push_prompt_{timestamp}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")
    return prompt_path


def run_test_case_gen(prompt_path: Path, timestamp: str) -> bool:
    """Invoke Test_Case_Gen/main.py with the generated prompt file."""
    main_py = PROJECT_ROOT / "Test_Case_Gen" / "main.py"
    output_subdir = OUTPUT_DIR / f"push_{timestamp}"
    output_subdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PYTHON_EXE,
        str(main_py),
        str(prompt_path),
        "--model", OLLAMA_MODEL,
        "--url",   OLLAMA_URL,
        "--output", str(output_subdir),
    ]

    log(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  🤖  AI Test Case Generator — Git Push Trigger")
    print("=" * 60)

    # Determine which repo to diff (default: the Ai_Test_Case_Gen repo itself)
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT
    repo_root = repo_root.resolve()

    log(f"Repo root : {repo_root}")
    log(f"Ollama    : {OLLAMA_MODEL} @ {OLLAMA_URL}")
    log(f"Blocking  : {'yes — push will fail if generation fails' if HOOK_BLOCKING else 'no — push continues regardless'}")
    print()

    # 1. Get changed Python files
    changed = get_changed_python_files(repo_root)

    if not changed:
        log("No Python files changed — skipping test case generation.", "WARN")
        print()
        sys.exit(0)

    log(f"Changed files ({len(changed)}):")
    for f in changed:
        print(f"       • {f.relative_to(repo_root)}")
    print()

    # 2. Build dynamic prompt
    log("Extracting features from changed files...")
    prompt_text = build_prompt(changed, repo_root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_path = save_prompt(prompt_text, timestamp)
    log(f"Prompt saved → {prompt_path}", "OK")

    # 3. Run generation
    log("Starting AI Test Case Generation pipeline...")
    print()
    success = run_test_case_gen(prompt_path, timestamp)
    print()

    if success:
        log(f"Test cases generated → {OUTPUT_DIR}/push_{timestamp}/test_cases.json", "OK")
        print()
        print("=" * 60)
        print("  ✅  Generation complete — push proceeding.")
        print("=" * 60)
        print()
        sys.exit(0)
    else:
        log("Test case generation FAILED.", "ERROR")
        print()
        if HOOK_BLOCKING:
            print("=" * 60)
            print("  ❌  Push BLOCKED. Fix the error above and try again.")
            print("      To skip: git push --no-verify")
            print("=" * 60)
            print()
            sys.exit(1)
        else:
            print("=" * 60)
            print("  ⚠️   Generation failed but HOOK_BLOCKING=false — push continuing.")
            print("=" * 60)
            print()
            sys.exit(0)


if __name__ == "__main__":
    main()
