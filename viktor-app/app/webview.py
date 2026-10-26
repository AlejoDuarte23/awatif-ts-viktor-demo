import base64
import json
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).parent / "web"


def render_webview(payload: dict[str, Any]) -> str:
    template = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    payload_base64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")

    return template.replace("__MODEL_PAYLOAD_BASE64__", payload_base64)
