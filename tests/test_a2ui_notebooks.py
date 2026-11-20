"""Check that the Python and JavaScript smoke tests exercise the same flow."""

import ast
import asyncio
import json
import subprocess
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


def javascript_flow():
    notebook = json.loads((CONTENT / "a2ui-js-form-submit.ipynb").read_text())
    code = "".join(notebook["cells"][1]["source"])
    script = """
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Surface {
  constructor() { this.batches = []; }
  send(messages) { this.batches.push(Array.isArray(messages) ? messages : [messages]); }
  onAction(handler) { this.handler = handler; }
}
const context = {A2UISurface: Surface, display: () => {}};
vm.createContext(context);
const code = input.code.replace(/^const \\{ A2UISurface \\} = await import\\([^\\n]+\\);\\n/, '');
if (code === input.code) throw new Error('JavaScript adapter import was not found');
vm.runInContext(code, context);
context.surface.handler(input.action);
console.log(JSON.stringify({batches: context.surface.batches, action: context.actionData}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps({"code": code, "action": ACTION}),
        text=True,
        capture_output=True,
        check=True,
    )
    output = json.loads(result.stdout)
    return output["batches"], output["action"]


class NotebookParityTest(unittest.TestCase):
    def test_python_wheel_and_javascript_assets_match(self):
        wheels = sorted((CONTENT.parent / "wheels").glob("a2ui_jupyter-*.whl"))
        self.assertEqual(len(wheels), 1, "Expected exactly one a2ui-jupyter wheel")
        with zipfile.ZipFile(wheels[0]) as wheel:
            for name in ("widget.js", "widget.css"):
                with self.subTest(asset=name):
                    self.assertEqual(
                        wheel.read(f"a2ui_jupyter/static/{name}"),
                        (CONTENT / "a2ui" / name).read_bytes(),
                    )

    def test_python_and_javascript_form_and_callback_match(self):
        python_batches, python_action = python_flow("smoke_test.ipynb")
        javascript_batches, javascript_action = javascript_flow()
        self.assertEqual(python_action, ACTION)
        self.assertEqual(javascript_action, ACTION)
        # Batch boundaries differ between the notebooks, so compare the message sequence.
        python_messages = [message for batch in python_batches for message in batch]
        javascript_messages = [message for batch in javascript_batches for message in batch]
        self.assertEqual(python_messages, javascript_messages)
        self.assertEqual(python_messages[-2]["updateDataModel"]["value"], "Submitted: Ada")
        self.assertEqual(
            python_messages[-1]["updateComponents"]["components"][0]["children"],
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
