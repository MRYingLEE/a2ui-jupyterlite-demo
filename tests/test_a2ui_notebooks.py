"""Check the Python notebook flow and its deployed widget assets."""

import json
import sys
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

CONTENT = Path(__file__).resolve().parents[1] / "content"
ACTION = {
    "version": "1.0",
    "action": {
        "name": "submit",
        "surfaceId": "manual-smoke-test",
        "sourceComponentId": "submit",
        "timestamp": "2026-11-11T00:00:00Z",
        "context": {"name": "Ada"},
    },
}


class Surface:
    def __init__(self):
        self.batches = []
        self.handler = None

    def send(self, messages):
        self.batches.append(messages if isinstance(messages, list) else [messages])

    def on_action(self, handler):
        self.handler = handler


class Action:
    def model_dump(self, **_kwargs):
        return ACTION


def python_flow(notebook_name):
    notebook = json.loads((CONTENT / notebook_name).read_text())
    code = "".join(notebook["cells"][2]["source"])
    module = types.ModuleType("a2ui_jupyter")
    module.A2UISurface = Surface
    display = types.ModuleType("IPython.display")
    display.display = lambda _surface: None
    ipython = types.ModuleType("IPython")
    ipython.display = display
    namespace = {}
    with patch.dict(
        sys.modules, {"a2ui_jupyter": module, "IPython": ipython, "IPython.display": display}
    ):
        exec(compile(code, notebook_name, "exec"), namespace)
    surface = namespace["surface"]
    surface.handler(Action())
    return surface.batches, namespace["action_data"]


class PythonNotebookTest(unittest.TestCase):
    def test_python_wheel_widget_assets_match_deployed_files(self):
        wheels = sorted((CONTENT.parent / "wheels").glob("a2ui_jupyter-*.whl"))
        self.assertEqual(len(wheels), 1, "Expected exactly one a2ui-jupyter wheel")
        with zipfile.ZipFile(wheels[0]) as wheel:
            for name in ("widget.js", "widget.css"):
                with self.subTest(asset=name):
                    self.assertEqual(
                        wheel.read(f"a2ui_jupyter/static/{name}"),
                        (CONTENT / "a2ui" / name).read_bytes(),
                    )

    def test_python_form_and_callback(self):
        for notebook_name in ("a2ui-test-pyodide.ipynb", "a2ui-test-xeus.ipynb"):
            with self.subTest(notebook=notebook_name):
                python_batches, python_action = python_flow(notebook_name)
                self.assertEqual(python_action, ACTION)
                self.assertEqual(python_batches[-1][0]["updateDataModel"]["value"], "Submitted: Ada")
                self.assertEqual(
                    python_batches[-1][1]["updateComponents"]["components"][0]["children"],
                    ["title", "status"],
                )

    def test_xeus_notebook_selects_xeus_kernel(self):
        notebook = json.loads((CONTENT / "a2ui-test-xeus.ipynb").read_text())
        self.assertEqual(notebook["metadata"]["kernelspec"]["name"], "xpython")


if __name__ == "__main__":
    unittest.main()
