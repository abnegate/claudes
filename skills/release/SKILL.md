---
name: release
description: Create a GitHub release with auto-generated changelog. Use this skill whenever the user wants to create a release, tag a release, publish a release, cut a release, or ship a version. Triggers on phrases like "release 1.2.3", "create a release", "tag a new version", "ship it", "cut a release", or any mention of creating GitHub releases.
argument-hint: "[[version]=auto|1.2.3|major|minor|patch, [branch]=main, [pre-release]=false]"
disable-model-invocation: true
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

### 3. Create the release

Run:

```bash
gh release create <version> \
  --title "<version>" \
  --generate-notes \
  --target <branch> \
  [--prerelease]
```

- `--generate-notes` auto-generates the changelog from merged PRs and commits since the last release
- `--target` specifies the branch (default `main`)
- `--prerelease` is added when pre-release is detected or explicitly requested

### 4. Confirm

After creation, display the release URL so the user can verify it. Run:

```bash
gh release view <version> --json url,tagName,isPrerelease,createdAt
```

## Examples

**Example 1 — explicit version:**
Prompt: release 1.2.3
Command: `gh release create 1.2.3 --title "1.2.3" --generate-notes --target main`

**Example 2 — bump keyword:**
Prompt: release patch
Latest tag: `1.2.3` → resolved version: `1.2.4`
Command: `gh release create 1.2.4 --title "1.2.4" --generate-notes --target main`

**Example 3 — bump keyword (major):**
Prompt: release major
Latest tag: `1.2.3` → resolved version: `2.0.0`
Command: `gh release create 2.0.0 --title "2.0.0" --generate-notes --target main`

**Example 4 — pre-release:**
Prompt: cut a release 2.0.0-beta.1 on the develop branch
Command: `gh release create 2.0.0-beta.1 --title "2.0.0-beta.1" --generate-notes --target develop --prerelease`

**Example 5 — explicit pre-release:**
Prompt: create release 3.1.0 on feature/v3 as a pre-release
Command: `gh release create 3.1.0 --title "3.1.0" --generate-notes --target feature/v3 --prerelease`

**Example 6 — bump keyword with no previous releases:**
Prompt: release minor
No previous release found → base: `0.0.0` → resolved version: `0.1.0`
Command: `gh release create 0.1.0 --title "0.1.0" --generate-notes --target main`

**Example 7 — auto-detect (no version provided):**
Prompt: create a release
Confirmation shown to user:
> **Previous version:** `1.2.3`
>
> **Changes since `1.2.3`:**
> - Features: `feat: add dark mode support`
> - Fixes: `fix: correct tooltip positioning`
> - Other: `chore: update dependencies`
>
> **Detected bump:** minor — new features detected
> **Proposed version:** `1.3.0`
>
> Proceed?

After user confirms → `gh release create 1.3.0 --title "1.3.0" --generate-notes --target main`

**Example 8 — auto-detect with breaking change:**
Prompt: ship it
Confirmation shown to user:
> **Previous version:** `2.1.0`
>
> **Changes since `2.1.0`:**
> - Breaking: `feat!: redesign authentication API`
> - Fixes: `fix: handle null user gracefully`
>
> **Detected bump:** major — breaking changes detected
> **Proposed version:** `3.0.0`
>
> Proceed?

After user confirms → `gh release create 3.0.0 --title "3.0.0" --generate-notes --target main`
