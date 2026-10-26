import importlib.util
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).parents[1] / "app"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODEL = load_module("base_plate_model_webview_test", APP_DIR / "model.py")
WEBVIEW = load_module("base_plate_webview_test", APP_DIR / "webview.py")

GeometryInputs = MODEL.GeometryInputs
LoadInputs = MODEL.LoadInputs
ViewInputs = MODEL.ViewInputs
build_payload = MODEL.build_payload
render_webview = WEBVIEW.render_webview


class TestWebView(unittest.TestCase):
    def test_generated_html_is_self_contained(self):
        payload = build_payload(
            GeometryInputs(),
            LoadInputs(),
            ViewInputs(),
            mode="model",
        )
        html = render_webview(payload)

        self.assertIn("window.__BASE_PLATE_PAYLOAD__", html)
        self.assertIn('font-family: "Roboto"', html)
        self.assertIn("data:font/ttf;base64,", html)
        self.assertIn('id="calculate-analysis" type="button"', html)
        self.assertIn('id="analysis-controls"', html)
        self.assertIn('id="deformation-scale"', html)
        self.assertIn("BasePlateSolver", html)
        self.assertNotIn("__MODEL_PAYLOAD_BASE64__", html)
        self.assertNotIn("/*__STYLES__*/", html)
        self.assertNotIn("/*__VIEWER_BUNDLE__*/", html)
        self.assertNotIn("__ROBOTO_400_BASE64__", html)
        self.assertNotIn("cdn.jsdelivr", html)
        self.assertNotIn("unpkg.com", html)
        self.assertNotIn("esm.sh", html)
        self.assertNotRegex(html, r"<script[^>]+src=")

    def test_payload_is_encoded_as_data(self):
        import base64
        import json
        import re

        payload = {"text": "</script><script>alert(1)</script> café ↑"}
        html = render_webview(payload)
        match = re.search(r'atob\("([^"\n]+)"\)', html)
        self.assertIsNotNone(match)
        decoded = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
        self.assertEqual(decoded, payload)
        self.assertNotIn(payload["text"], html)
        self.assertIn("TextDecoder", html)


if __name__ == "__main__":
    unittest.main()
