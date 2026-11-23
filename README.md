# A2UI JupyterLite test site

This repository builds a JupyterLite site for testing the A2UI Jupyter
renderer with Pyodide, xeus-python, and JavaScript kernels. It is based on
the [JupyterLite demo](https://github.com/jupyterlite/demo).

The renderer and reusable examples live in
[`typescript/renderers/jupyter`](https://github.com/MRYingLEE/a2ui/tree/jupyter-js-kernel/typescript/renderers/jupyter)
and [`python/a2ui_jupyter`](https://github.com/MRYingLEE/a2ui/tree/jupyter-python-kernel/python/a2ui_jupyter)
in the A2UI source checkout. This repository owns the site configuration and
kernel-specific smoke tests.

## Requirements

JupyterLite requires a modern browser. See the
[JupyterLite documentation](https://jupyterlite.readthedocs.io/) for browser
requirements and deployment instructions.

See [`requirements.txt`](requirements.txt) for the JupyterLite extensions, the
Pyodide packages, and the `jupyterlite-xeus` addon that builds the xeus-python
kernel. The xeus-python environment is defined in
[`environment.yml`](environment.yml); building it requires `micromamba` on
`PATH`.

## A2UI test notebooks

- [`content/smoke_test.ipynb`](content/smoke_test.ipynb) is the form test for
  every kernel. Select Python (Pyodide) or Python (XPython) before running it.
  Its setup cell sets `KERNEL` to the detected kernel. On Pyodide, the cell
  installs the package with `piplite` when it is missing. On xeus-python, the
  package must already be in the environment built from
  [`environment.yml`](environment.yml).
- `content/01_text_and_layout.ipynb` through `content/06_agent_function_call.ipynb`
  are copies of the examples in the
  [a2ui-jupyter package](https://github.com/MRYingLEE/a2ui-jupyter/tree/main/python/a2ui_jupyter/examples).
  They use the same setup cell as the smoke test.
- [`content/a2ui-js-form-submit.ipynb`](content/a2ui-js-form-submit.ipynb)
  tests the same form and callback with the JavaScript kernel. It resolves the
  adapter relative to the site, including on GitHub Pages project sites.
- [`content/javascript.ipynb`](content/javascript.ipynb) continues to exercise the JavaScript kernel.

The [GitHub Pages workflow](.github/workflows/deploy.yml) builds the Pyodide
package index from `requirements.txt` and the xeus-python runtime from
[`environment.yml`](environment.yml). [jupyter-lite.json](jupyter-lite.json)
pins Pyodide to 0.29.3 to match the local `rpds-py` wheel. The workflow builds
pushes to `main` and `jupyter-js-kernel` and pull requests. Only `main`
deploys to Pages; download the workflow's build artifact or build locally to
try the JavaScript branch. Do not set
`baseUrl` in [jupyter-lite.json](jupyter-lite.json): the root page compares it
with its own path to redirect to `/lab/`, and an override such as `../` breaks
that redirect.

The xeus-python build mounts [`startup/a2ui_preload.pth`](startup/a2ui_preload.pth)
so the kernel imports the mounted `rpds` module at startup. Importing it later
suspends the kernel and runs the next queued cell before the current cell
finishes, which showed up as `NameError` when the setup and surface cells were
run back to back.

The wheel in [`wheels/`](wheels) and the JavaScript files in
[`content/a2ui/`](content/a2ui) are deployment inputs. When testing a renderer
change, rebuild and replace both from the same A2UI revision; changing the
source checkout alone does not update the deployed site. Restart the kernels
and refresh the browser after rebuilding.

Run the local form-parity check with
`python -m unittest discover -s tests -p 'test_a2ui_notebooks.py'`. It compares
the messages and callback results in both notebooks; it does not replace the
browser tests for each kernel.


