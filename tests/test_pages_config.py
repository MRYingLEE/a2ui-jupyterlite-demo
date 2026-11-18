"""Guard the Pages build preconditions P1 to P3 of the tab-servers design.

Source checks run anywhere. Set PAGES_DIST to a built site to also check its
config, extension folders, and installed package versions.
"""

import importlib.metadata
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_KERNEL_EXTENSION = "@jupyterlite/javascript-kernel-extension"
TESTED_PINS = {
    "jupyterlite-core": "0.8.7",
    "jupyterlite-javascript-kernel": "0.4.0a5",
}


def load_config(path):
    return json.loads(path.read_text(encoding="utf-8"))["jupyter-config-data"]


def requirement_pins(text):
    pins = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==(\S+)$", line.strip())
        if match:
            pins[match.group(1)] = match.group(2)
    return pins


class PagesPreconditionTest(unittest.TestCase):
    def test_source_config_exposes_app_in_browser(self):
        config = load_config(ROOT / "jupyter-lite.json")
        self.assertEqual(config.get("exposeAppInBrowser"), "true")

    def test_source_config_keeps_javascript_kernel_enabled(self):
        config = load_config(ROOT / "jupyter-lite.json")
        self.assertNotIn(JS_KERNEL_EXTENSION, config.get("disabledExtensions", []))

    def test_requirements_pin_tested_versions(self):
        pins = requirement_pins((ROOT / "requirements.txt").read_text(encoding="utf-8"))
        for name, version in TESTED_PINS.items():
            with self.subTest(package=name):
                self.assertEqual(pins.get(name), version)

    def test_built_site_meets_preconditions(self):
        dist = os.environ.get("PAGES_DIST")
        if not dist:
            self.skipTest("PAGES_DIST is not set")
        site = Path(dist)
        config = load_config(site / "jupyter-lite.json")
        self.assertEqual(config.get("exposeAppInBrowser"), "true")
        self.assertNotIn(JS_KERNEL_EXTENSION, config.get("disabledExtensions", []))
        self.assertTrue((site / "extensions" / JS_KERNEL_EXTENSION).is_dir())
        for name, version in TESTED_PINS.items():
            with self.subTest(package=name):
                self.assertEqual(importlib.metadata.version(name), version)


if __name__ == "__main__":
    unittest.main()
