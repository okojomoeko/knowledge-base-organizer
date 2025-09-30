# knowledge-base-organizer

This is a Python project template based on the `uv`, package and project manager. The goal of this template is to provide a structured and maintainable foundation for new Python projects.

## Prerequisites

Before you start using this template, make sure you have the following installed:

- `uv` (https://docs.astral.sh/uv/#getting-started)

## Set up uv development environment

To set up the uv development environment, follow these steps:

1. Install development tools and packages by running the following command inside the `.venv` virtual environment:

    ```sh
    uv sync
    ```

2. **Activate Virtual Environment**: Ensure that you have activated your virtual environment by running:

    ```sh
    source .venv/bin/activate
    ```

3. **Run Pre-Commit Hooks**: To ensure code quality and consistency, run the pre-commit hooks before making any commits. This can be done by executing the following commands:

   ```sh
   uv run pre-commit install -t pre-commit -t pre-push
   ```

## Usage

This template uses `nox` for running various tasks (refer to `noxfile.py`). Here are some common commands you might use:

- **Run Tests**: To execute all tests, run:

  ```sh
  nox -s pytest
  ```

- **Linting**: To check your code for linting errors, run:

  ```sh
  nox -s lint
  ```

- **Building Documentation**: To build the documentation, run:

  ```sh
  nox -s docs
  ```

You can run `pytest`, `ruff`, `sphinx-build` individually, if needed.
See `noxfile.py` for more details on available tasks

## Reference

Upgrade dependencies in `pyproject.toml` using `uv`.

- https://gist.github.com/yhoiseth/c80c1e44a7036307e424fce616eed25e
