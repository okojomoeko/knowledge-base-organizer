"""Noxfile."""

import sys

import nox

python_versions = ["3.13"] if sys.version_info >= (3, 13) else ["default"]
nox.options.default_venv_backend = "uv"


@nox.session(python=python_versions)
def pytest(session: nox.Session) -> None:
    """Run pytest."""
    session.run("uv", "sync", "--group", "dev", "--reinstall")
    session.run("uv", "run", "pytest")


@nox.session()
def lint(session: nox.Session) -> None:
    """Run ruff formatter and linter."""
    session.run("uv", "sync", "--group", "dev", "--reinstall")
    session.run("uv", "run", "ruff", "format", "--preview", "src", "tests")
    session.run(
        "uv",
        "run",
        "ruff",
        "check",
        "--fix",
        "--preview",
        "src",
        "tests",
        "--exclude",
        "experiments",
    )
    # or
    # session.run("uvx", "ruff", "format", "--preview", "src", "tests")
    # session.run("uvx", "ruff", "check", "--fix", "--preview", "src", "tests")


@nox.session()
def lizard(session: nox.Session) -> None:
    """Run lizard for calculating CCN."""
    session.run("uv", "sync", "--group", "dev")
    session.run(
        "uv",
        "run",
        "lizard",
        "--languages=python",
        "--CCN=20",
        "--length=100",
        "--arguments=5",
        "--exclude=experiments/*",
        "src",
        "tests",
    )


@nox.session()
def docs(session: nox.Session) -> None:
    """Build sphinx documentation."""
    session.run("uv", "sync", "--group", "doc", "--reinstall")
    session.run(
        "uv",
        "run",
        "sphinx-apidoc",
        "-o",
        "docs/source",
        "src/knowledge_base_organizer",
    )
    session.run("uv", "run", "sphinx-build", "-M", "html", "docs/source", "docs/build")
