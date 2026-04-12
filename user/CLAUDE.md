# Global Instructions

## General Rules

- Before using any SDK, CLI, or API, verify the current version and its actual API surface. Do NOT guess dependency versions, class names, or method signatures — check docs and package registries first.

## Naming

- Prefer single-word names over two-word names when context makes the meaning obvious. e.g. `connections` not `backendConnections` when there's only one set of connections, `pools` not `backendPools`, `timeout` not `connectTimeout` when it's the only timeout. Drop redundant qualifiers.
- Don't abbreviate names. Use full words: `certificate` not `cert`, `connection` not `conn`, `request` not `req`, `message` not `msg`, etc. Well-known acronyms (TLS, HTTP, TCP, CA) are fine.
- Acronyms in method/function names should be camelCase: `updateMfa()` not `updateMFA()`. Uppercase acronyms break SDK generation (`create_m_f_a` instead of `create_mfa`). In non-method identifiers (constants, config keys), fully capitalise: `cacheTTL`, `parseURL`.
- Don't double up namespace in file names. e.g. `Engine/Driver.php` not `Engine/EngineDriver.php` — namespace already provides context. Put implementations in nested subdirectories (e.g. `Engine/Driver/{Postgres,MySQL,Mongo}.php`).
- REST endpoints: plural nouns (`/collections` not `/collection`), kebab-case for multi-word paths (`/acme-challenge` not `/acmeChallenge`).

## Code Style

- Never use "section header" style comments like `// ---` or `// ===` and if you see any, remove them.
- Prefer typed config objects over associative arrays/maps.
- Use readonly classes with typed constructor properties where the language supports it.
- Use constants or enums instead of magic strings.
- Don't impose arbitrary limits (max file sizes, max entries, etc.) unless there's a real technical constraint. Validate claimed sizes against actual file/container size instead.
- Full type hints on all parameters and return types. Catch errors at compile time, not runtime.
- One class/interface per file. Filename matches class name.
- Imports: alphabetical, one per statement, grouped by const/class/function.
- Single quotes for strings by default. Double quotes only when the string contains a single quote.
- Sparse updates — when updating a record, pass only changed attributes, not the full object.
- Domain-driven design — group business logic by domain. No helper files, no random global functions, no fat controllers.
- When working in a file, fix any nearby violations of the above rules.

## PHP

- Singular nouns for namespaces: `Adapter` not `Adapters` — a namespace is a folder, plurality is implied.
- When extending a Utopia library in Appwrite or Cloud, use `src/Utopia` namespace: `Appwrite\Utopia\Database\Adapter\MySQL` not `Appwrite\Database\Adapter\MySQL`.
- Dependency versions: use `*` wildcard not `~`/`^` ranges. `"utopia-php/framework": "0.33.*"` not `"~0.33.0"`.
- First-class callable syntax: `$this->action(...)` not `[$this, 'action']`.
- Use `array_push($items, ...$new)` instead of `$items = array_merge($items, $new)` in loops — merge copies the entire array every iteration.
- Use `array_values()` after `unset()` or `array_unique()` to re-index and keep the array a list.
- `??` (null coalescing) for null/isset checks. `?:` (elvis) for falsy checks. `getenv()` never returns null, so use `?:` with it.
- Prefer `assertSame` over `assertEquals` in new PHPUnit tests — assertSame checks type and value.

## Testing

- There are no "pre-existing issues". If tests fail, fix them, regardless of when you think the issue was introduced.
- Every bug fix must include a regression test that fails without the fix and passes with it.

## Workflow

- Don't stop mid-implementation to ask if I want to review. Keep going until success criteria is reached. Unnecessary pauses are disruptive.
- Always parallelise as much as possible. For multi-file implementation tasks, use the consolidation pattern (worktree-isolated agents + consolidator merge). For independent non-overlapping work (research, linting, testing), launch concurrent subagents in a single message. Sequential execution of independent work is unacceptable.
- Never revert PR changes to work around missing dependencies. Add the dependency properly (e.g. as a VCS repository in `composer.json`).
- Never use shims or patch files for local dependencies. Edit source in the dependency repo, commit and push, then run the package manager update in the consuming repo.
- Format and lint before every commit. PHP: `composer lint` (Pint, PSR-12). Kotlin: ktlint. Rust: `cargo fmt` + `cargo clippy -D warnings`. JS/TS: Prettier.
- Conventional commits: `(type): subject` — types are `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`. Focus on "why" not "what".
- In Appwrite repos, PRs target the current version branch (e.g. `1.9.x`), not `main`. `main` is reserved for release management.
- Once work is finalised and I confirm it's good, clean up before stopping. Delete dead code, failed attempts, abandoned files, temporary branches, commented-out earlier iterations, `// TODO: remove` markers, debug logging, scratch scripts, and anything else that was only useful during the iteration. Don't leave "loose ends" or "we can migrate this later" notes in the final state — finish them. The last commit of a finished change should be ready to review as if the earlier iterations never happened.

## Multi-Agent Coordination

- For any multi-part task, use the **consolidation** skill pattern: decompose into subtasks, launch all subtasks as parallel worktree-isolated agents (`isolation: "worktree"`), then merge with the **consolidator** agent (`subagent_type: "consolidator"`). Worktrees give each agent its own repo copy — overlapping file edits are expected and handled at merge time.
- Never serialize work just because agents touch the same file. That's what worktree isolation and the consolidator are for.
- Default to parallel. Sequential execution of independent work is unacceptable. If in doubt whether tasks are independent, they probably are — launch them in worktrees and let the consolidator sort it out.

## Claude Code Plugin Development

- When creating slash commands or skills for Claude Code plugins, always use the `commands/` directory format (not `skills/`). Slash commands must be placed in `.claude/commands/` to be visible.

## Android / Jetpack Compose

- When modifying UI composables (especially wrapping in `AnimatedVisibility`, adding/removing containers), always verify that ALL sibling elements remain visible and correctly structured. Check that section headers, dividers, and other structural elements aren't accidentally hidden.
- When making visual/UI refinements (gradients, colors, spacing, sizing), make the MINIMAL change requested. Do not proactively change related visual properties unless explicitly asked. If iterating on visual tuning, present 2-3 options with descriptions rather than guessing.

## Release Process

- Always bump version numbers (`plugin.json`, `build.gradle`, `package.json`) as part of any release or publishing workflow. Do not wait to be reminded.

## Projects

All repos live in `~/Local/`. Primary ecosystem is Appwrite — backend platform, cloud hosting, edge, SDKs for 11+ languages, console, database/query libraries, and supporting infrastructure (proxy, websocket, audit, cache, framework). Most backend services are PHP 8.3+ on Swoole 6. Utopia PHP framework throughout — no Laravel/Symfony.