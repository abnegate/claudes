---
name: pr
description: Create a pull request with proper description
argument-hint: "[title]"
disable-model-invocation: true
allowed-tools: Bash, Read, Grep
---

# Create Pull Request

Create a GitHub pull request with comprehensive description.

## Execution Steps

1. **Gather context**:
   ```bash
   git status
   git log main..HEAD --oneline
   git diff main...HEAD --stat
   ```

2. **Check remote sync**:
   ```bash
   git fetch origin
   git rev-list --left-right --count origin/main...HEAD
   ```

3. **Push if needed**:
   ```bash
   git push -u origin $(git branch --show-current)
   ```

4. **Create PR**:
   ```bash
   gh pr create --title "$TITLE" --body "$(cat <<'EOF'
   ## Summary
   - Bullet point summary of changes

   ## Changes
   - Detailed list of what changed

   ## Test plan
   - [ ] Tests pass locally
   - [ ] Manual testing completed
   - [ ] No regressions

   ## Screenshots (if UI changes)
   N/A
   EOF
   )"
   ```

## PR Title Format

Use conventional commit style:
- `feat: Add new feature`
- `fix: Resolve bug in X`
- `refactor: Improve Y structure`

## If `$ARGUMENTS` Provided

Use as PR title. Otherwise, generate from commits.

## Output

Return the PR URL when complete.

## Checklist Before PR

- [ ] All tests pass
- [ ] Code is formatted (`./gradlew ktlintFormat`)
- [ ] No secrets in code
- [ ] SDK regenerated if API changed
