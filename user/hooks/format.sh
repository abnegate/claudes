#!/bin/bash
# Post-edit formatter hook (PostToolUse on Write|Edit)
# Reads hook JSON from stdin, extracts file_path, formats based on extension.
# Outputs additionalContext JSON so Claude knows the file was reformatted.

set -uo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    pass
" 2>/dev/null)

[ -z "$FILE" ] && exit 0
[ ! -f "$FILE" ] && exit 0

EXT="${FILE##*.}"
FORMATTED=false

case "$EXT" in
  php)
    [ -f vendor/bin/pint ] && vendor/bin/pint "$FILE" >/dev/null 2>&1 && FORMATTED=true
    ;;
  js|ts|jsx|tsx|mjs|mts)
    if [ -f node_modules/.bin/prettier ]; then
      npx prettier --write "$FILE" >/dev/null 2>&1 && FORMATTED=true
    elif command -v prettier >/dev/null 2>&1; then
      prettier --write "$FILE" >/dev/null 2>&1 && FORMATTED=true
    fi
    ;;
  kt|kts)
    if command -v ktlint >/dev/null 2>&1; then
      ktlint -F "$FILE" >/dev/null 2>&1 && FORMATTED=true
    fi
    ;;
  rs)
    if command -v cargo >/dev/null 2>&1; then
      cargo fmt >/dev/null 2>&1 && FORMATTED=true
    fi
    ;;
esac

if [ "$FORMATTED" = true ]; then
  python3 -c "
import json
print(json.dumps({'additionalContext': 'Auto-formatted ${FILE} — re-read before next edit.'}))
" 2>/dev/null
fi

exit 0
