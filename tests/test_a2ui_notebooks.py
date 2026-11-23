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


def javascript_flow(notebook_name: str, iframe: bool = True):
    notebook = json.loads((CONTENT / notebook_name).read_text())
    code = "".join(notebook["cells"][1]["source"])
    script = """
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Surface {
  constructor() { this.batches = []; }
  send(messages) { this.batches.push(Array.isArray(messages) ? messages : [messages]); }
  onAction(handler) { this.handler = handler; }
}
const site = 'https://example.test/a2ui-jupyterlite-demo/';
const context = {
  URL,
  display: () => {},
  importAdapter: async url => {
    if (url !== `${site}files/a2ui/kernel.js`) throw new Error(`Wrong adapter URL: ${url}`);
    return {A2UISurface: Surface};
  },
};
if (input.iframe) {
  context.document = {baseURI: `${site}lab/index.html`};
} else {
  context.location = {
    href: `${site}extensions/@jupyterlite/javascript-kernel-extension/static/worker.js`,
  };
}
vm.createContext(context);
const code = input.code.replace('await import(', 'await importAdapter(');
vm.runInContext(`(async () => {\\n${code}\\n})()`, context).then(() => {
  context.surface?.handler?.(input.action);
  console.log(JSON.stringify({
    batches: context.surface?.batches ?? [],
    action: context.actionData ?? null,
  }));
}).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps({"code": code, "action": ACTION, "iframe": iframe}),
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
        javascript_batches, javascript_action = javascript_flow("a2ui-js-form-submit.ipynb")
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

    def test_javascript_smoke_notebooks_load_adapter_under_site_prefix(self):
        for notebook in ("a2ui-js-form-submit.ipynb", "a2ui-js-kernel-smoke.ipynb"):
            for iframe in (True, False):
                with self.subTest(notebook=notebook, iframe=iframe):
                    javascript_flow(notebook, iframe)

    def test_notebooks_share_the_setup_cell(self):
        setup_cells = {
            path.name: "".join(json.loads(path.read_text())["cells"][1]["source"])
            for path in NOTEBOOKS
        }
        self.assertEqual(len(set(setup_cells.values())), 1, setup_cells.keys())


if __name__ == "__main__":
    unittest.main()
