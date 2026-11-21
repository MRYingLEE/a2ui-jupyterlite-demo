"""Check the Python notebook flow and its deployed widget assets."""

import ast
import asyncio
import json
import sys
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

CONTENT = Path(__file__).resolve().parents[1] / "content"
NOTEBOOKS = sorted(CONTENT.glob("[0-9][0-9]_*.ipynb")) + [CONTENT / "smoke_test.ipynb"]

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
        for cell in notebook["cells"][1:3]:
            code = compile(
                "".join(cell["source"]),
                notebook_name,
                "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )
            result = eval(code, namespace)
            if asyncio.iscoroutine(result):
                asyncio.run(result)
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
        python_batches, python_action = python_flow("smoke_test.ipynb")
        self.assertEqual(python_action, ACTION)
        self.assertEqual(python_batches[-1][0]["updateDataModel"]["value"], "Submitted: Ada")
        self.assertEqual(
            python_batches[-1][1]["updateComponents"]["components"][0]["children"],
            ["title", "status"],
        )

    def test_notebooks_share_the_setup_cell(self):
        setup_cells = {
            path.name: "".join(json.loads(path.read_text())["cells"][1]["source"])
            for path in NOTEBOOKS
        }
        self.assertEqual(len(set(setup_cells.values())), 1, setup_cells.keys())


if __name__ == "__main__":
    unittest.main()
