import pytest
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Search upwards for .env
load_dotenv(find_dotenv())

def get_env():
    return {
        "email_user": os.getenv("EMAIL_USER") or os.getenv("EMAIL_ADDRESS"),
        "email_pass": os.getenv("EMAIL_PASS") or os.getenv("EMAIL_PASSWORD"),
    }

def load_config(env):
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    config = data.get("default", {})
    env_data = data.get(env, {})
    config.update(env_data)
    
    return config

@pytest.fixture(scope="session")
def config(request):
    env = request.config.getoption("--env")
    base_config = load_config(env)
    env_config = get_env()
    base_config.update(env_config)
    return base_config

