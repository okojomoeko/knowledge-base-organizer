#!/bin/bash

set -euo pipefail

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Function to display usage ---
usage() {
  echo "Usage: $0 /path/to/markdown/folder --template /path/to/template.md"
  echo ""
  echo "  Checks if markdown files in a directory contain all frontmatter properties"
  echo "  defined in a template file."
  echo ""
  echo "Arguments:"
  echo "  /path/to/markdown/folder    Directory containing markdown files to check."
  echo "  --template /path/to/template.md  Path to the template markdown file."
  exit 1
}

# --- Argument Parsing ---
if [ "$#" -ne 3 ]; then
  usage
fi

TARGET_DIR="$1"
TEMPLATE_FLAG="$2"
TEMPLATE_FILE="$3"

if [ "$TEMPLATE_FLAG" != "--template" ]; then
    echo -e "${RED}エラー: 不正なオプションです: $TEMPLATE_FLAG${NC}"
    usage
fi

# --- Validate Arguments ---
if [ ! -d "$TARGET_DIR" ]; then
  echo -e "${RED}エラー: 指定されたディレクトリが見つかりません: $TARGET_DIR${NC}"
  exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo -e "${RED}エラー: 指定されたテンプレートファイルが見つかりません: $TEMPLATE_FILE${NC}"
  exit 1
fi

# --- Dynamic Property Extraction from Template ---
echo "--- テンプレートからプロパティを抽出中... ---"
echo "テンプレートファイル: $TEMPLATE_FILE"

# テンプレートのFrontmatterからプロパティ名を抽出し、配列に格納 (bash v3互換)
# 1. --- と --- の間の行を取得
# 2. 1行目と最終行の --- を削除
# 3. : 以降を削除してキー名のみにする
# 4. 空行を削除
PROPERTIES=()
while IFS= read -r line; do
    # 空行は追加しない
    if [[ -n "$line" ]]; then
        PROPERTIES+=("$line")
    fi
done < <(sed -n '/^---$/,/^---$/p' "$TEMPLATE_FILE" | sed '1d;$d' | sed 's/:.*//' | sed '/^\s*$/d')


if [ ${#PROPERTIES[@]} -eq 0 ]; then
    echo -e "${RED}エラー: テンプレートファイルからプロパティを抽出できませんでした。${NC}"
    exit 1
fi

# --- Script Main Logic ---
echo "--- Frontmatterチェックを開始します ---"
echo "対象ディレクトリ: $TARGET_DIR"
echo "チェック項目: ${PROPERTIES[*]}"
echo "-------------------------------------"

overall_issue_found=false

find "$TARGET_DIR" -type f \( -name "*.md" -o -name "*.markdown" \) | while read -r file; do
  frontmatter=$(sed -n '/^---$/,/^---$/p' "$file" | sed '1d;$d')

  if [ -z "$frontmatter" ]; then
    echo -e "${YELLOW}警告: Frontmatterが見つかりません: $file${NC}"
    continue
  fi

  missing_properties=()
  for prop in "${PROPERTIES[@]}"; do
    if ! echo "$frontmatter" | grep -q -E "^\s*${prop}\s*:"; then
      missing_properties+=("$prop")
    fi
  done

  if [ ${#missing_properties[@]} -ne 0 ]; then
    overall_issue_found=true
    echo -e "FILE: $file"
    for missing in "${missing_properties[@]}"; do
      echo -e "  - ${RED}不足: ${missing}${NC}"
    done
    echo ""
  fi
done

echo "-------------------------------------"

if [ "$overall_issue_found" = false ]; then
  echo -e "${GREEN}✅ すべてのファイルのFrontmatterに問題はありませんでした。${NC}"
else
  echo -e "${RED}⚠️ いくつかのファイルでプロパティの不足が見つかりました。${NC}"
fi
