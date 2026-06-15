import os
import yaml

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_base_dir() -> str:
    return _BASE_DIR


def load_config() -> dict:
    config_path = os.path.join(_BASE_DIR, "config.yml")
    with open(config_path) as f:
        return yaml.safe_load(f)
