---
description: Create git commits in logical groups for all current changes
---

# Smart Commit

Create logically grouped git commits following project conventions.

## Commit Message Format

```
(<type>): <description>
```
- No body
- No multi-line string
- No co-authors

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
4. Analyze changes
5. Determine logical groups of features in current diff
6. Generate appropriate messages
7. Use type prefix based on changes
8. Stage relevant files with `git add`
9. Create commit with HEREDOC format:
   ```bash
   git commit -m "$(cat <<'EOF'
   (type): description
   EOF
   )"
   ```
10. Repeat for each logical group of changes
11. Run `git status` to verify

## Safety Rules

- NEVER commit `.env` or credential files
- NEVER use `--amend` unless explicitly requested
- NEVER push
- NEVER skip hooks with `--no-verify`

## Example

```bash
git add server/http/src/main/kotlin/
git commit -m "$(cat <<'EOF'
(feat): Add user preferences endpoint
EOF
)"
```
