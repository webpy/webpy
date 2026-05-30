Development setup
=================

web.py supports Python 3.10 and newer. A virtual environment is recommended so
the editable install, test dependencies, and code quality tools do not affect
the system Python installation.

Create and activate a virtual environment from the repository root::

    python3 -m venv .venv
    source .venv/bin/activate

On Windows PowerShell, activate it with::

    .venv\Scripts\Activate.ps1

Install web.py in editable mode with its runtime and test dependencies::

    python -m pip install --upgrade pip
    python -m pip install --editable .
    python -m pip install -r test_requirements.txt

Install pre-commit and enable the repository hooks::

    python -m pip install pre-commit
    pre-commit install

If commits were created before the hooks were installed, run the hooks across
the existing tree once::

    pre-commit run --all-files

The hooks run Black, codespell, Ruff, validate-pyproject, and pyproject-fmt.
The same tools are also run by the GitHub Actions workflow. If Ruff reports
fixable issues without changing files, install Ruff in the environment and run
it directly::

    python -m pip install ruff
    ruff check --fix .

Run the test suite with pytest::

    pytest

The full CI job also configures MariaDB and PostgreSQL service databases before
running tests. See ``.github/workflows/lint_python.yml`` for the database
environment variables used by the workflow.
