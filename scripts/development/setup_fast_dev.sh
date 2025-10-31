#!/bin/bash
# Script: Fast Development Environment Setup
# Purpose: 高速な開発環境とDXの最適化
# Usage: ./scripts/development/setup_fast_dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

main() {
    log_info "Setting up fast development environment..."

    cd "$PROJECT_ROOT"

    # 1. 高速なruffチェック（基本ルールのみ）
    log_info "Running fast ruff check..."
    uv run ruff check --select=E,F,W,I,UP,B --fix src/ tests/

    # 2. フォーマット実行
    log_info "Running ruff format..."
    uv run ruff format src/ tests/

    # 3. 基本テスト実行（高速）
    log_info "Running fast tests..."
    uv run pytest -x --tb=short

    log_success "Fast development setup completed!"
}

main "$@"
