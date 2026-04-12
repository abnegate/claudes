#!/bin/bash
# Failure detection auto-continue hook (PostToolUse on Bash)
# Checks if a test/build/lint/format/analyze command failed,
# then injects additionalContext telling Claude to fix it.

set -uo pipefail

INPUT=$(cat)

CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('command', '') if isinstance(ti, dict) else str(ti))
except:
    pass
" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# Only trigger on test/build/lint/format/analyze commands
CMD_LOWER=$(echo "$CMD" | tr '[:upper:]' '[:lower:]')
MATCH=false
for KEYWORD in test build lint check compile format analyse analyze \
  gradle gradlew phpunit pest jest vitest mocha pytest unittest \
  "cargo test" "cargo build" "cargo check" "cargo clippy" \
  "go test" "go build" "go vet" \
  "npm run" "npm test" npx yarn pnpm \
  "composer test" "composer lint" "composer check" "composer analyse" "composer analyze" \
  "make test" "make build" "make check" \
  mvn "dotnet test" "dotnet build" \
  "swift test" "swift build" "flutter test" \
  tsc eslint phpstan psalm mypy pylint rubocop rustfmt ktlint prettier pint; do
  if echo "$CMD_LOWER" | grep -qF "$KEYWORD"; then
    MATCH=true
    break
  fi
done

[ "$MATCH" = false ] && exit 0

# Check tool output for failure patterns
OUTPUT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    o = d.get('tool_output', d.get('stdout', ''))
    print(o if isinstance(o, str) else str(o))
except:
    pass
" 2>/dev/null)

# Also check $TOOL_OUTPUT env var as fallback
if [ -z "$OUTPUT" ] && [ -n "${TOOL_OUTPUT:-}" ]; then
  OUTPUT="$TOOL_OUTPUT"
fi

[ -z "$OUTPUT" ] && exit 0

# Comprehensive failure pattern matching
FAILED=false
TAIL=$(echo "$OUTPUT" | tail -100)
for PATTERN in \
  "FAIL" "FAILED" "FAILURE" \
  "ERROR" "ERRORS" "Error:" "error:" "error[" \
  "Exception" "exception" \
  "fatal" "Fatal" "FATAL" \
  "BUILD FAILED" "Build failed" \
  "ERRORS FOUND" \
  "ABORT" "Aborted" \
  "panic:" "PANIC" \
  "Segmentation fault" "core dumped" \
  "Traceback" "SyntaxError" "TypeError" "ReferenceError" \
  "NullPointerException" "ClassNotFoundException" \
  "compilation failed" "compile error" "Compile error" \
  "AssertionError" "assertion failed" "AssertionError" "assert" \
  "ENOENT" "EACCES" "EPERM" \
  "cannot find module" "Could not resolve" "Module not found" \
  "timed out" "TIMEOUT" \
  "exit code 1" "exit code 2" "exit status 1" "exit status 2" \
  "exited with" "non-zero" \
  "Tests:.*failed" "tests failed" "test failed"; do
  if echo "$TAIL" | grep -qiF "$PATTERN" 2>/dev/null || echo "$TAIL" | grep -qi "$PATTERN" 2>/dev/null; then
    FAILED=true
    break
  fi
done

[ "$FAILED" = false ] && exit 0

# Inject fix directive as additionalContext
python3 -c "
import json
print(json.dumps({
    'additionalContext': (
        'FAILURE DETECTED in test/build/lint command. '
        'Diagnose the root cause from the error output and fix it now. '
        'Do not report the failure without attempting a fix. '
        'Do not ask the user what to do. '
        'Read the error, identify the cause, and fix it. '
        'Try at least 3 meaningfully different approaches before escalating.'
    )
}))
" 2>/dev/null

exit 0
