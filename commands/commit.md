---
description: Create a git commit with conventional commit message
argument-hint: "[message]"
---

# Smart Commit

Create a git commit following project conventions.

## Commit Message Format

```
(<type>): <description>
```

No body, no co-authors.

## Types

| Type | Use For |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `refactor` | Code restructuring |
| `docs` | Documentation |
| `test` | Tests |
| `chore` | Maintenance |
| `perf` | Performance |
| `style` | Formatting |

## Execution Steps

1. Run `git status` to see changes (never use `-uall`)
2. Run `git diff --staged` and `git diff` to understand changes
3. Run `git log --oneline -5` to see recent commit style
4. If `$ARGUMENTS` provided, use as commit message
5. If no `$ARGUMENTS`:
   - Analyze changes
   - Generate appropriate message
   - Use type prefix based on changes
6. Stage relevant files with `git add`
7. Create commit with HEREDOC format:
   ```bash
   git commit -m "$(cat <<'EOF'
   (type): description
   EOF
   )"
   ```
8. Run `git status` to verify

## Safety Rules

- NEVER commit `.env` or credential files
- NEVER use `--amend` unless explicitly requested
- NEVER use `--force` push
- NEVER skip hooks with `--no-verify`

## Example

```bash
git add server/http/src/main/kotlin/
git commit -m "$(cat <<'EOF'
(feat): Add user preferences endpoint
EOF
)"
```
