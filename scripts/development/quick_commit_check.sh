#!/bin/bash
# Script: Quick Commit Check
# Purpose: 高速なコミット前チェック（必須項目のみ）
# Usage: ./scripts/development/quick_commit_check.sh

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

main() {
    log_info "Running quick commit checks..."

    cd "$PROJECT_ROOT"

    # 1. 高速フォーマット
    log_info "Formatting code..."
    if ! uv run ruff format src/ tests/; then
        log_error "Formatting failed"
        exit 1
    fi

    # 2. 必須ルールのみチェック
    log_info "Running essential lint checks..."
    if ! uv run ruff check --select=F,W,I,UP --fix src/ tests/; then
        log_error "Essential lint checks failed"
        exit 1
    fi

    # 3. 高速テスト（失敗時即停止）
    log_info "Running fast tests..."
    if ! uv run pytest -x --tb=short --maxfail=3 -k "not (test_summarize_command or test_get_llm_config_with_custom_path or test_global_function_integration or test_error_handling_integration or test_keyword_extraction_with_real_data or test_connection_suggestions_with_real_data)"; then
        log_error "Tests failed"
        exit 1
    fi

    log_success "All quick checks passed! Ready to commit."
}

main "$@"
