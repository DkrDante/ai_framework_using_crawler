import os
import json
from typing import Dict, Any, List

def read_text_file(file_path: str) -> str:
    """Reads all text from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def normalize_test_cases(data: Any) -> Dict[str, Any]:
    """Ensures test cases data complies with the requested schema."""
    if not isinstance(data, dict) or "test_cases" not in data:
        if isinstance(data, list):
            tc_list = data
        elif isinstance(data, dict) and len(data) == 1 and isinstance(list(data.values())[0], list):
            tc_list = list(data.values())[0]
        else:
            tc_list = []
    else:
        tc_list = data["test_cases"]
        
    normalized = []
    for idx, tc in enumerate(tc_list):
        if not isinstance(tc, dict):
            continue
        priority = str(tc.get("priority") or "Medium").strip().capitalize()
        if priority not in ["High", "Medium", "Low"]:
            priority = "Medium"
            
        # Parse requirements
        reqs = tc.get("requirements", [])
        if isinstance(reqs, str):
            reqs = [reqs]
        elif not isinstance(reqs, list):
            reqs = []
        reqs = [str(r).strip() for r in reqs if r]

        # Parse validation (UI, API, or both)
        val_input = tc.get("validation", [])
        if isinstance(val_input, str):
            val_list = [v.strip() for v in val_input.replace(";", ",").split(",")]
        elif isinstance(val_input, list):
            val_list = val_input
        else:
            val_list = []
        
        validation = []
        for val in val_list:
            val_str = str(val).upper().strip()
            if val_str in ["UI", "API"]:
                validation.append(val_str)
        
        # Deduplicate while preserving order
        validation = list(dict.fromkeys(validation))
        if not validation:
            validation = ["UI"] # Default fallback
        
        # Parse URL
        tc_url = tc.get("url")
        if isinstance(tc_url, str):
            tc_url = tc_url.strip()
            if not tc_url or tc_url.lower() == "null":
                tc_url = None
        else:
            tc_url = None
            
        normalized.append({
            "id": str(tc.get("id") or f"TC-{idx+1:03d}").strip(),
            "title": str(tc.get("title") or f"Verify Test Case {idx+1}").strip(),
            "priority": priority,
            "url": tc_url,
            "validation": validation,
            "requirements": reqs,
            "preconditions": [str(p).strip() for p in tc.get("preconditions", [])] if isinstance(tc.get("preconditions"), list) else [],
            "steps": [str(step).strip() for step in tc.get("steps", [])] if isinstance(tc.get("steps"), list) else [],
            "expected_result": str(tc.get("expected_result") or "").strip()
        })
    return {"test_cases": normalized}

def export_to_json(data: Dict[str, Any], name: str, output_dir: str) -> str:
    """Saves structured dictionary to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{name}.json")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return json_path
