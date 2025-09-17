import json, re, yaml, pathlib

DEFAULT = {
    "forbidden": [],
    "require_citation": True,
    "json_schema_keys": ["answer", "citations"],
}

def load_policies(path="guardrails/policies.yaml"):
    p = pathlib.Path(path)
    if not p.exists():
        return DEFAULT
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "forbidden": data.get("forbidden", DEFAULT["forbidden"]),
        "require_citation": bool(data.get("require_citation", DEFAULT["require_citation"])),
        "json_schema_keys": data.get("json_schema_keys", DEFAULT["json_schema_keys"]),
    }

def extract_json_block(text: str):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def check_json_ok(payload, required_keys):
    return isinstance(payload, dict) and all(k in payload for k in required_keys)

def check_citation(payload_or_text):
    if isinstance(payload_or_text, dict):
        c = payload_or_text.get("citations", [])
        return isinstance(c, list) and len(c) > 0
    return ("출처" in payload_or_text) or ("citation" in payload_or_text.lower())

def check_forbidden(text: str, words):
    return any(w in text for w in words)