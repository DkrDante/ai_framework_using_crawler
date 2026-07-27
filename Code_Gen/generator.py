"""
Code Generator — Diff-Aware Core

For each URL group of test cases, this module:

1. Scans existing files in `automation-framework/tests/ai_generated/`
2. Extracts which TC IDs are already covered (via AST function-name parsing)
3. Computes three sets:
     NEW      — TC IDs in spec but not in any existing file  → generate & append/create
     EXISTING — TC IDs already covered                       → leave untouched
     ORPHANED — TC IDs in existing files but NOT in spec     → delete the function
4. Writes the minimum diff back to disk.

This means successive pipeline runs are idempotent and incremental.
"""

import ast
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_utils.logger import get_logger
from Code_Gen.constants.prompts import CODEGEN_SYSTEM_PROMPT, CODEGEN_USER_TEMPLATE

logger = get_logger("code_generator")


# ---------------------------------------------------------------------------
# Ollama API
# ---------------------------------------------------------------------------

def _call_ollama(model: str, system_prompt: str, user_prompt: str, ollama_url: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
        "options": {"num_ctx": 32768, "temperature": 0.1},
    }
    try:
        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=600)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Could not connect to Ollama at {ollama_url}.")
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama API timed out.")
    except Exception as exc:
        raise RuntimeError(f"Ollama API failed: {exc}") from exc

    content: str = resp.json().get("message", {}).get("content", "")
    if not content:
        raise ValueError("Empty content from Ollama.")
    return content


# ---------------------------------------------------------------------------
# Python code helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$",          "", text.strip())
    return text.strip()


def _is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError as err:
        logger.warning(f"Syntax error in generated code: {err}")
        return False


def _to_snake(title: str) -> str:
    s = re.sub(r"[^\w\s]", "", title.lower())
    return re.sub(r"\s+", "_", s.strip())


def _to_pascal(title: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[\s_\-]+", title))


# ---------------------------------------------------------------------------
# TC-ID ↔ function-name encoding
# Each generated function name embeds the TC ID so we can reliably detect it.
#   TC-001 → test_TC_001_verify_...
# ---------------------------------------------------------------------------

_TC_ID_RE = re.compile(r"^test_(TC[_\-]\d+)_", re.IGNORECASE)


def _fn_name_for_tc(tc: Dict[str, Any]) -> str:
    tc_id_safe = tc["id"].replace("-", "_")
    slug = _to_snake(tc["title"])[:60]
    return f"test_{tc_id_safe}_{slug}"


def _tc_id_from_fn(fn_name: str) -> Optional[str]:
    """Extract TC ID from a function name like test_TC_001_verify_..."""
    m = _TC_ID_RE.match(fn_name)
    if not m:
        return None
    return m.group(1).replace("_", "-")   # TC_001 → TC-001


# ---------------------------------------------------------------------------
# Existing file analysis
# ---------------------------------------------------------------------------

def _scan_existing_file(path: Path) -> Dict[str, Tuple[int, int]]:
    """
    Parse an existing AI-generated test file and return a mapping:
        tc_id → (start_line, end_line)   (1-indexed, inclusive)
    of every function that embeds a TC ID in its name.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        logger.warning(f"Could not parse {path}: {exc}")
        return {}

    lines = source.splitlines()
    coverage: Dict[str, Tuple[int, int]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tc_id = _tc_id_from_fn(node.name)
        if tc_id is None:
            continue
        start = node.lineno        # 1-indexed
        end   = node.end_lineno    # 1-indexed
        coverage[tc_id] = (start, end)

    return coverage


def _scan_all_existing(ai_dir: Path) -> Dict[str, Dict[str, Tuple[int, int]]]:
    """
    Returns {file_path_str: {tc_id: (start, end)}} for every .py in ai_dir
    that has at least one recognisable TC function.
    """
    result: Dict[str, Dict[str, Tuple[int, int]]] = {}
    for py_file in ai_dir.glob("test_ai_*.py"):
        coverage = _scan_existing_file(py_file)
        if coverage:
            result[str(py_file)] = coverage
    return result


# ---------------------------------------------------------------------------
# Delete orphaned functions from a file
# ---------------------------------------------------------------------------

def _delete_functions_from_file(path: Path, tc_ids_to_delete: Set[str]) -> int:
    """
    Remove functions whose TC ID is in tc_ids_to_delete from *path*.
    Returns the number of functions removed.
    """
    coverage = _scan_existing_file(path)
    # Which lines to delete?
    lines_to_remove: Set[int] = set()
    removed = 0
    source_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    for tc_id, (start, end) in sorted(coverage.items(), key=lambda x: x[1][0], reverse=True):
        if tc_id not in tc_ids_to_delete:
            continue
        # Also capture any decorator lines immediately before the def
        dec_start = start - 1  # 0-indexed
        while dec_start > 0 and source_lines[dec_start - 1].strip().startswith("@"):
            dec_start -= 1
        for i in range(dec_start, end):  # 0-indexed
            lines_to_remove.add(i)
        removed += 1

    if not lines_to_remove:
        return 0

    kept = [line for i, line in enumerate(source_lines) if i not in lines_to_remove]
    # Strip trailing blank lines that were left by deletions, but keep one separator
    text = "".join(kept).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    return removed


# ---------------------------------------------------------------------------
# Append new test functions to an existing file
# ---------------------------------------------------------------------------

def _append_functions_to_file(path: Path, new_code: str) -> None:
    """
    Append only the top-level function definitions from new_code to path.
    (Skips imports / module-level statements that already exist.)
    """
    try:
        tree = ast.parse(new_code)
    except SyntaxError:
        logger.warning("Cannot parse new_code for appending — writing raw block.")
        existing = path.read_text(encoding="utf-8")
        path.write_text(existing.rstrip() + "\n\n\n" + new_code.strip() + "\n")
        return

    new_lines = new_code.splitlines(keepends=True)
    fn_blocks: List[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tc_id = _tc_id_from_fn(node.name)
        if tc_id is None:
            continue
        start = node.lineno - 1    # 0-indexed
        end   = node.end_lineno    # exclusive upper bound (0-indexed)
        # Capture decorators
        dec_start = start
        while dec_start > 0 and new_lines[dec_start - 1].strip().startswith("@"):
            dec_start -= 1
        block = "".join(new_lines[dec_start:end])
        fn_blocks.append(block.rstrip())

    if not fn_blocks:
        logger.warning("No TC functions found in new code to append.")
        return

    existing = path.read_text(encoding="utf-8").rstrip()
    separator = "\n\n\n"
    path.write_text(existing + separator + separator.join(fn_blocks) + "\n")


# ---------------------------------------------------------------------------
# URL / page helpers
# ---------------------------------------------------------------------------

def _group_by_url(test_cases: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for tc in test_cases:
        url = tc.get("url") or "no_url"
        groups.setdefault(url, []).append(tc)
    return groups


def _page_label(url: str) -> str:
    if url == "no_url":
        return "general"
    try:
        from urllib.parse import urlparse
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        return parts[-1] if parts else "home"
    except Exception:
        return "home"


def _load_elements(output_dir: str, url: str) -> str:
    label = _page_label(url)
    path = Path(output_dir) / label / "elements.json"
    if not path.exists():
        return "[]"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        compact = json.dumps(data[:60], indent=2)
        return compact[:6000] + ("\n... (truncated)" if len(compact) > 6000 else "")
    except Exception as exc:
        logger.warning(f"Could not load elements: {exc}")
        return "[]"


# ---------------------------------------------------------------------------
# LLM generation for a list of test cases
# ---------------------------------------------------------------------------

def _generate_code_for_tcs(
    tcs: List[Dict],
    elements_ctx: str,
    output_filename: str,
    class_name: str,
    model: str,
    ollama_url: str,
    max_retries: int,
) -> Optional[str]:
    user_prompt = CODEGEN_USER_TEMPLATE.format(
        test_cases_json=json.dumps({"test_cases": tcs}, indent=2),
        elements_context=elements_ctx,
        output_filename=output_filename,
        class_name=class_name,
    )
    for attempt in range(1, max_retries + 2):
        logger.info(f"Calling Ollama (attempt {attempt}/{max_retries + 1}) for {len(tcs)} TC(s)...")
        raw  = _call_ollama(model, CODEGEN_SYSTEM_PROMPT, user_prompt, ollama_url)
        code = _strip_fences(raw)
        if _is_valid_python(code):
            return code
        logger.warning(f"Attempt {attempt} produced invalid Python — retrying...")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DiffResult:
    """Summary of what the generator did for one URL group."""
    def __init__(self, label: str):
        self.label   = label
        self.file    = ""
        self.added   : List[str] = []
        self.retained: List[str] = []
        self.deleted : List[str] = []
        self.action  = ""   # "created" | "updated" | "unchanged"


def generate_test_code(
    test_cases_path: str,
    output_dir: str,
    framework_tests_dir: str,
    model: str,
    ollama_url: str,
    max_retries: int = 2,
) -> List[DiffResult]:
    """
    Diff-aware entry point.

    1. Reads test_cases.json
    2. Scans existing ai_generated/ files for covered TC IDs
    3. For each URL group:
       - deletes orphaned TC functions
       - generates code only for NEW TCs
       - appends to existing file OR creates a new file
    4. Returns a list of DiffResult (one per URL group)
    """
    # ── Load spec ────────────────────────────────────────────────────────────
    with open(test_cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    spec_tcs: List[Dict] = data.get("test_cases", [])
    if not spec_tcs:
        raise ValueError("test_cases.json is empty.")

    spec_ids: Set[str] = {tc["id"] for tc in spec_tcs}

    # ── Ensure output dir + __init__.py ──────────────────────────────────────
    ai_dir = Path(framework_tests_dir)
    ai_dir.mkdir(parents=True, exist_ok=True)
    init_f = ai_dir / "__init__.py"
    if not init_f.exists():
        init_f.write_text('"""AI-generated tests package."""\n')

    # ── Scan all existing files ───────────────────────────────────────────────
    # file_path_str → {tc_id → (start, end)}
    existing_coverage = _scan_all_existing(ai_dir)

    # Flat map: tc_id → file_path_str  (which file already covers it)
    tc_to_file: Dict[str, str] = {}
    for fp, cov in existing_coverage.items():
        for tc_id in cov:
            tc_to_file[tc_id] = fp

    # ── Find orphaned IDs (in files but NOT in spec) ──────────────────────────
    all_covered_ids: Set[str] = set(tc_to_file.keys())
    orphaned_ids: Set[str]    = all_covered_ids - spec_ids

    if orphaned_ids:
        logger.info(f"Orphaned TC IDs to delete: {sorted(orphaned_ids)}")
        # Group orphans by file
        orphans_by_file: Dict[str, Set[str]] = {}
        for tc_id in orphaned_ids:
            fp = tc_to_file[tc_id]
            orphans_by_file.setdefault(fp, set()).add(tc_id)
        for fp, ids in orphans_by_file.items():
            n = _delete_functions_from_file(Path(fp), ids)
            logger.info(f"Deleted {n} orphaned function(s) from {fp}")

    # ── Group spec TCs by URL ─────────────────────────────────────────────────
    groups = _group_by_url(spec_tcs)
    results: List[DiffResult] = []

    for url, tcs in groups.items():
        label          = _page_label(url)
        output_filename = f"test_ai_{label}.py"
        class_name     = f"TestAI{_to_pascal(label)}"
        out_path       = ai_dir / output_filename
        elements_ctx   = _load_elements(output_dir, url)

        result         = DiffResult(label)
        result.file    = str(out_path)

        # ── Classify each TC in this group ───────────────────────────────────
        new_tcs:      List[Dict] = []
        retained_ids: List[str] = []

        for tc in tcs:
            if tc["id"] in tc_to_file:
                retained_ids.append(tc["id"])
            else:
                new_tcs.append(tc)

        # Orphans in this file that were already removed above
        file_orphans = [
            tc_id for tc_id in orphaned_ids
            if tc_to_file.get(tc_id) == str(out_path)
        ]

        result.retained = retained_ids
        result.deleted  = file_orphans

        logger.info(
            f"[{label}] new={len(new_tcs)} | "
            f"retained={len(retained_ids)} | "
            f"deleted={len(file_orphans)}"
        )

        # ── Nothing to generate ───────────────────────────────────────────────
        if not new_tcs and not file_orphans:
            result.action = "unchanged"
            results.append(result)
            logger.info(f"[{label}] No changes needed.")
            continue

        # ── Generate code for NEW TCs only ────────────────────────────────────
        if new_tcs:
            generated = _generate_code_for_tcs(
                tcs=new_tcs,
                elements_ctx=elements_ctx,
                output_filename=output_filename,
                class_name=class_name,
                model=model,
                ollama_url=ollama_url,
                max_retries=max_retries,
            )

            if generated is None:
                logger.error(f"[{label}] Failed to generate valid code. Skipping.")
                continue

            if out_path.exists():
                # Append new functions to the existing file
                _append_functions_to_file(out_path, generated)
                result.action = "updated"
                logger.info(f"[{label}] Appended {len(new_tcs)} new TC(s) to {out_path}")
            else:
                # Write brand-new file
                out_path.write_text(generated, encoding="utf-8")
                result.action = "created"
                logger.info(f"[{label}] Created new file {out_path}")

            result.added = [tc["id"] for tc in new_tcs]

        elif file_orphans:
            # Only deletions happened (no new TCs)
            result.action = "updated"

        results.append(result)

    return results
