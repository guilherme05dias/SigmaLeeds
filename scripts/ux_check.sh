#!/usr/bin/env bash
# Conta violações conhecidas de UX/UI no frontend.
# Uso: bash scripts/ux_check.sh
# Saída: tabela com contagem. Compare antes/depois de mudanças.

cd "$(dirname "$0")/.."

count() {
    local label="$1"; shift
    local n; n="$("$@" 2>/dev/null | wc -l)"
    printf "%-40s %s\n" "$label" "$n"
}

echo "=== UX/UI violation counts ($(date +%H:%M:%S)) ==="
count "Google Fonts links"             grep -hE "fonts.googleapis|googleapis.com" templates/index.html static/style.css
count "Hex hardcoded em HTML"          grep -hnE '#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\b' templates/index.html
count "Emoji unicode (↓ literal)"      grep -hnF "↓" templates/index.html static/script.js
count "Token --color-bg-surface órfão" grep -hnE "color-bg-surface" static/script.js
count "alert()/confirm() em JS"        grep -hE "\balert\(|\bconfirm\(" static/script.js
count "Botão só-ícone sem aria-label"  bash -c "grep -hE '<button[^>]*onclick[^>]*><i data-lucide' templates/index.html static/script.js | grep -v 'aria-label'"
count "Typo 'sera(o)'"                 grep -hnF "sera(o)" static/script.js
count "Inline style com 5+ propriedades" bash -c "grep -hE 'style=\"[^\"]*;[^\"]*;[^\"]*;[^\"]*;[^\"]*' templates/index.html"

echo ""
echo "Para zerar (meta):"
echo "  Google Fonts: 0       Hex em HTML: 0       Emoji: 0"
echo "  bg-surface órfão: 0   Typo: 0              Botões sem aria-label: 0"
echo "  alert/confirm: ainda 23+ (refactor para modal está adiado)"
