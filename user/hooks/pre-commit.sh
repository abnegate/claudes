#!/bin/bash
# Pre-commit formatter hook (PreToolUse on Bash git commit)
# Formats all staged files by language, then re-stages them.

set -uo pipefail

# PHP
STAGED_PHP=$(git diff --cached --name-only --diff-filter=ACM -- '*.php' 2>/dev/null | head -50)
if [ -n "$STAGED_PHP" ] && [ -f vendor/bin/pint ]; then
  echo "$STAGED_PHP" | tr '\n' '\0' | xargs -0 vendor/bin/pint >/dev/null 2>&1
  echo "$STAGED_PHP" | tr '\n' '\0' | xargs -0 git add 2>/dev/null
fi

# JS / TS
STAGED_JS=$(git diff --cached --name-only --diff-filter=ACM -- '*.js' '*.ts' '*.jsx' '*.tsx' '*.mjs' '*.mts' 2>/dev/null | head -50)
if [ -n "$STAGED_JS" ]; then
  if [ -f node_modules/.bin/prettier ]; then
    echo "$STAGED_JS" | tr '\n' '\0' | xargs -0 npx prettier --write >/dev/null 2>&1
    echo "$STAGED_JS" | tr '\n' '\0' | xargs -0 git add 2>/dev/null
  elif command -v prettier >/dev/null 2>&1; then
    echo "$STAGED_JS" | tr '\n' '\0' | xargs -0 prettier --write >/dev/null 2>&1
    echo "$STAGED_JS" | tr '\n' '\0' | xargs -0 git add 2>/dev/null
  fi
fi

# Kotlin
STAGED_KT=$(git diff --cached --name-only --diff-filter=ACM -- '*.kt' '*.kts' 2>/dev/null | head -50)
if [ -n "$STAGED_KT" ] && command -v ktlint >/dev/null 2>&1; then
  echo "$STAGED_KT" | tr '\n' '\0' | xargs -0 ktlint -F >/dev/null 2>&1
  echo "$STAGED_KT" | tr '\n' '\0' | xargs -0 git add 2>/dev/null
fi

# Rust
STAGED_RS=$(git diff --cached --name-only --diff-filter=ACM -- '*.rs' 2>/dev/null | head -50)
if [ -n "$STAGED_RS" ] && command -v cargo >/dev/null 2>&1; then
  cargo fmt >/dev/null 2>&1
  echo "$STAGED_RS" | tr '\n' '\0' | xargs -0 git add 2>/dev/null
fi

exit 0
