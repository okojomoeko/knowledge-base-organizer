#!/bin/bash
# Script: Full Check
# Purpose: 完全なコード品質チェック（全ルール）
# Usage: ./scripts/development/full_check.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log_info() {
    echo "ℹ️  $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_success() {
    echo "✅ $1"
}

log_warning() {
    echo "⚠️  $1"
}

main() {
    log_info "Running full code quality checks..."

    cd "$PROJECT_ROOT"

    # 1. フォーマット
    log_info "Formatting code..."
    if ! uv run ruff format src/ tests/; then
        log_error "Formatting failed"
        exit 1
    fi

    # 2. 完全なlintチェック
    log_info "Running complete lint checks..."
    if ! uv run ruff check src/ tests/; then
        log_warning "Some lint issues found. Review and fix manually if needed."
        # 完全チェックでは警告として扱い、続行する
    fi

    # 3. 型チェック
    log_info "Running type checks..."
    if ! uv run mypy src/; then
        log_warning "Type check issues found. Review and fix if needed."
    fi

    # 4. 完全なテスト実行
    log_info "Running all tests..."
    if ! uv run pytest --cov=src/knowledge_base_organizer --cov-report=term-missing; then
        log_error "Tests failed"
        exit 1
    fi

    # 5. セキュリティチェック
    log_info "Running security checks..."
    if ! uv run bandit -r src/ -f json -o bandit-report.json; then
        log_warning "Security issues found. Check bandit-report.json"
    fi

    log_success "Full checks completed!"
}

main "$@"
