# A2UI JupyterLite test site

This branch builds a JupyterLite site for testing the A2UI Jupyter renderer
with Python kernels, Pyodide and xeus-python. It is based on the
[JupyterLite demo](https://github.com/jupyterlite/demo).

The renderer and reusable examples live in
[`typescript/renderers/jupyter`](https://github.com/MRYingLEE/a2ui-jupyter/tree/main/typescript/renderers/jupyter)
and [`python/a2ui_jupyter`](https://github.com/MRYingLEE/a2ui-jupyter/tree/main/python/a2ui_jupyter)
in the A2UI source checkout. This repository owns the site configuration and
Python-kernel smoke tests. JavaScript-kernel examples and tests are on the
`jupyter-js-kernel` branch.

## Requirements

JupyterLite requires a modern browser. See the
[JupyterLite documentation](https://jupyterlite.readthedocs.io/) for browser
requirements and deployment instructions.

See [`requirements.txt`](requirements.txt) for the JupyterLite extensions and
Pyodide packages and [`environment.yml`](environment.yml) for the xeus-python
environment.

## A2UI Python test notebooks

- [`content/a2ui-test.ipynb`](content/a2ui-test.ipynb) is the same form test
  for Pyodide and xeus-python. Select the kernel before running it. If the
  package is missing, the setup cell uses `piplite` in Pyodide; the xeus-python
  environment is built with the package already installed. The form callback
  replaces the form with a confirmation and stores the action for inspection
  in the last cell.
- [`content/a2ui-test-xeus.ipynb`](content/a2ui-test-xeus.ipynb) and
  [`content/manual_smoke_test.ipynb`](content/manual_smoke_test.ipynb) point
  to the shared Python test for existing links.

The [GitHub Pages workflow](.github/workflows/deploy.yml) builds the Pyodide
package index from `requirements.txt` and the xeus-python runtime from
[`environment.yml`](environment.yml). [jupyter-lite.json](jupyter-lite.json)
pins Pyodide to 0.29.3 to match the local `rpds-py` wheel. The workflow deploys
pushes to `main`; other branches run the build without deploying. When serving locally,
pass `--base-url=../` to `jupyter lite serve` for the `/lab/` and `/notebooks/`
routes.

The wheel in [`wheels/`](wheels) and the widget files in
[`content/a2ui/`](content/a2ui) are deployment inputs. When testing a renderer
change, rebuild and replace both from the same A2UI revision; changing the
source checkout alone does not update the deployed site. Restart the kernels
and refresh the browser after rebuilding.

Run the local notebook check with
`python -m unittest discover -s tests -p 'test_a2ui_notebooks.py'`. It checks
the Python form callback and confirms that the wheel contains the deployed
widget files; it does not replace browser testing.


