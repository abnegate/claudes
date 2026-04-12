---
description: "Create a GitHub release with auto-generated changelog. Use this skill whenever the user wants to create a release, tag a release, publish a release, cut a release, or ship a version. Triggers on phrases like \"release 1.2.3\", \"create a release\", \"tag a new version\", \"ship it\", \"cut a release\", or any mention of creating GitHub releases."
argument-hint: "[[version]=auto|1.2.3|major|minor|patch, [branch]=main, [pre-release]=false]"
---

# GitHub Release

Create a GitHub release using the `gh` CLI with auto-generated changelog from all changes since the last release.

## Arguments

The user provides these in natural language — extract them from the prompt:

- **version** (optional): An explicit semver tag without `v` prefix (e.g. `1.2.3`, `2.0.0-beta.1`), a semver bump keyword (`major`, `minor`, `patch`), or omitted entirely to auto-detect the bump type from the changelog.
- **branch** (optional): Branch to create the tag/release on. Defaults to `main`.
- **pre-release** (optional): Explicitly mark as pre-release. Auto-detected if the version contains `alpha`, `beta`, or `rc` (e.g. `1.0.0-rc.1`).

## Workflow

### 1. Resolve the version

**If no version was provided** (auto-detect from changelog):

1. Fetch the latest release tag:
   ```bash
   gh release list --limit 1 --json tagName --jq '.[0].tagName'
   ```
2. Strip any `v` prefix from the tag to get the current version. If no previous release exists, use `0.0.0` as the base.
3. Generate the changelog between the last release and HEAD:
   ```bash
   git log <latest-tag>..HEAD --pretty=format:"%s" --no-merges
   ```
   If there is no previous release, use `git log --pretty=format:"%s" --no-merges` to get all commits.
4. Classify each commit message using conventional commit prefixes and keywords to determine the bump type:
   - **major** — any commit contains a `BREAKING CHANGE` trailer, or has a `!` after the type (e.g. `feat!:`, `fix!:`), or the message explicitly mentions "breaking change", or you infer an API change is not backward compatible
   - **minor** — any commit starts with `feat:` or `feat(…):`, or the message describes new functionality (new feature, add support for, introduce, etc.)
   - **patch** — everything else: `fix:`, `chore:`, `docs:`, `refactor:`, `perf:`, `test:`, `ci:`, `style:`, `build:`, bug fixes, dependency updates, etc.
   The highest-priority classification wins: major > minor > patch.
5. **Present a confirmation summary to the user and wait for approval before proceeding.** The summary must include:
   - **Previous version**: the current latest release tag
   - **Changes**: a categorised list of commits since that tag (grouped by type: breaking, features, fixes, other)
   - **Detected bump**: the inferred bump type and why (e.g. "minor — new features detected")
   - **Proposed version**: the computed next version

   Do NOT proceed to create the release until the user explicitly confirms.

**If the user provided a bump keyword** (`major`, `minor`, or `patch`):

1. Fetch the latest release tag:
   ```bash
   gh release list --limit 1 --json tagName --jq '.[0].tagName'
   ```
2. Strip any `v` prefix from the tag to get the current version. If no previous release exists, use `0.0.0` as the base.
3. Bump the appropriate component:
   - `major`: increment MAJOR, reset MINOR and PATCH to 0 (e.g. `1.2.3` → `2.0.0`)
   - `minor`: increment MINOR, reset PATCH to 0 (e.g. `1.2.3` → `1.3.0`)
   - `patch`: increment PATCH (e.g. `1.2.3` → `1.2.4`)
4. Show the user the resolved version and confirm before proceeding.

**If the user provided an explicit version string:**

Confirm the version string is valid semver. It should match the pattern `MAJOR.MINOR.PATCH` with an optional pre-release suffix like `-alpha.1`, `-beta.2`, or `-rc.1`. Reject anything with a `v` prefix — strip it and inform the user if they include one.

### 2. Determine pre-release status

A release is pre-release if:
- The version contains `-alpha`, `-beta`, or `-rc` (e.g. `1.0.0-beta.1`)
- The user explicitly says it's a pre-release

### 3. Build the changelog

Fetch all commits since the last release:

```bash
git log <latest-tag>..HEAD --pretty=format:"%s" --no-merges
```

If no previous release, use `git log --pretty=format:"%s" --no-merges`.

Classify each commit by its conventional commit prefix and group into sections:

- **New Features** — `feat:` or `feat(…):` prefixed commits
- **Bug Fixes** — `fix:` or `fix(…):` prefixed commits
- **Other Changes** — everything else (`refactor:`, `chore:`, `docs:`, `perf:`, `test:`, `style:`, `build:`, `ci:`)

Within each section, list commits as bullet points. Strip the type prefix for readability (e.g. `(feat): add planner agent` becomes `Add planner agent`). Capitalise the first letter. Keep the description concise.

Omit empty sections. If a section has no commits, don't include it.

Format the body as:

```markdown
## New Features

- Add planner agent for task decomposition
- Add verifier agent for plan validation

## Bug Fixes

- Restore swoole API surfaces stripped during compression
- Remove arbitrary subtask limit from consolidation skill

## Other Changes

- Compress android-expert skill — remove training-redundant content
- Rename elite-fullstack-architect -> architect, code-griller -> reviewer
- Update commands to use consolidation pattern for parallel work
```

### 4. Create the release

```bash
gh release create <version> \
  --title "<version>" \
  --notes "$(cat <<'EOF'
[changelog body from step 3]
EOF
)" \
  --target <branch> \
  [--prerelease]
```

Use `--notes` with the hand-crafted changelog, NOT `--generate-notes`.

### 5. Confirm

After creation, display the release URL:

```bash
gh release view <version> --json url,tagName,isPrerelease,createdAt
```

## Examples

**Explicit version:**
Prompt: `release 1.2.3`
1. Build changelog from commits since last tag
2. `gh release create 1.2.3 --title "1.2.3" --notes "[changelog]" --target main`

**Auto-detect:**
Prompt: `create a release`
1. Fetch last tag (`1.2.3`), classify commits, detect bump (minor — new features)
2. Show confirmation with changelog preview and proposed version (`1.3.0`)
3. After user confirms: `gh release create 1.3.0 --title "1.3.0" --notes "[changelog]" --target main`

**Pre-release:**
Prompt: `cut a release 2.0.0-beta.1 on develop`
1. `gh release create 2.0.0-beta.1 --title "2.0.0-beta.1" --notes "[changelog]" --target develop --prerelease`
