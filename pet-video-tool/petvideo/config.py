import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    llm = cfg.setdefault("llm", {})
    llm["api_key"] = os.environ.get("LLM_API_KEY", "")
    llm["base_url"] = os.environ.get("LLM_BASE_URL", llm.get("base_url", "https://api.deepseek.com"))
    llm["model"] = os.environ.get("LLM_MODEL", llm.get("model", "deepseek-chat"))
    return cfg


def resolve(p):
    if not p:
        return None
    p = Path(os.path.expanduser(str(p)))
    return p if p.is_absolute() else ROOT / p
