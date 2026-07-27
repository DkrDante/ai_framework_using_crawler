import os
import sys
import json
import requests
from typing import Dict, Any

# Add root path to sys.path so we can import shared utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_utils.logger import get_logger
from Test_Case_Gen.constants.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from Test_Case_Gen.utils.helpers import (
    normalize_test_cases,
    export_to_json
)

# Initialize Logger
logger = get_logger("generator")

def call_ollama(
    model: str, 
    system_prompt: str, 
    user_prompt: str, 
    ollama_url: str = "http://localhost:11434"
) -> Dict[str, Any]:
    """Calls local Ollama API forcing JSON response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "num_ctx": 32768,  
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=500)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Could not connect to Ollama at {ollama_url}. "
            "Please ensure Ollama is installed and running locally."
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama API request timed out. Try with a smaller document or check your local GPU usage.")
    except Exception as e:
        raise RuntimeError(f"Ollama API request failed: {str(e)}")
        
    result = response.json()
    content = result.get("message", {}).get("content", "")
    
    if not content:
        raise ValueError("Received empty content from Ollama API.")
        
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse Ollama response as JSON. Raw content was:\n{content}")

def generate_test_cases(
    txt_content: str, 
    model: str, 
    ollama_url: str, 
    output_dir: str
) -> Dict[str, Any]:
    """Generates detailed QA test cases mapping to extracted requirements from plain text."""
    logger.info("Initiating Ollama call for test case generation...")
    user_prompt = USER_PROMPT_TEMPLATE.format(txt_content=txt_content)
    
    raw_data = call_ollama(model, SYSTEM_PROMPT, user_prompt, ollama_url)
    normalized = normalize_test_cases(raw_data)
    export_to_json(normalized, "test_cases", output_dir)
    return normalized
