"""Noxfile."""

import sys

import nox

python_versions = ["3.13"] if sys.version_info >= (3, 13) else ["default"]
nox.options.default_venv_backend = "uv"


@nox.session(python=python_versions)
def pytest(session: nox.Session) -> None:
    """Run pytest."""
    # 高速化: --reinstallを削除し、必要時のみsync
    session.run("uv", "sync", "--group", "dev")
    session.run("uv", "run", "pytest")


@nox.session()
def lint(session: nox.Session) -> None:
    """Run ruff formatter and linter."""
    # 高速化: --reinstallを削除、uvxを使用してさらに高速化
    session.run("uvx", "ruff", "format", "src", "tests")
    session.run(
        "uvx", "ruff", "check", "--fix", "src", "tests", "--exclude", "experiments"
    )


@nox.session()
def lizard(session: nox.Session) -> None:
    """Run lizard for calculating CCN."""
    # 高速化: uvxを使用
    session.run(
        "uvx",
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
    # 高速化: --reinstallを削除
    session.run("uv", "sync", "--group", "doc")
    session.run(
        "uv",
        "run",
        "sphinx-apidoc",
        "-o",
        "docs/source",
        "src/knowledge_base_organizer",
    )
    session.run("uv", "run", "sphinx-build", "-M", "html", "docs/source", "docs/build")


# 高速開発用セッション
@nox.session()
def fast_check(session: nox.Session) -> None:
    """Fast development checks - essential rules only."""
    session.run("uvx", "ruff", "format", "src", "tests")
    session.run("uvx", "ruff", "check", "--select=F,W,I,UP", "--fix", "src", "tests")
    session.run("uv", "run", "pytest", "-x", "--tb=short")


@nox.session()
def security(session: nox.Session) -> None:
    """Run security checks with relaxed settings."""
    session.run("uv", "sync", "--group", "dev")
    # banditを緩い設定で実行
    session.run(
        "uv",
        "run",
        "bandit",
        "-c",
        "bandit.yaml",
        "-r",
        "src",
        "--severity-level",
        "medium",
    )
    # pip-auditを重要度の高い脆弱性のみチェック
    session.run(
        "uv",
        "run",
        "pip-audit",
        "--ignore-vuln=GHSA-4xh5-x5gv-qwph",
        "--severity-threshold=high",
    )
