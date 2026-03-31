# Naming

- Prefer single-word names over two-word names when context makes the meaning obvious. e.g. `connections` not `backendConnections` when there's only one set of connections, `pools` not `backendPools`, `timeout` not `connectTimeout` when it's the only timeout. Drop redundant qualifiers.
- Don't abbreviate names. Use full words: `certificate` not `cert`, `connection` not `conn`, `request` not `req`, `message` not `msg`, etc. Well-known acronyms (TLS, HTTP, TCP, CA) are fine.
- Acronyms in method/function names should be camelCase: `updateMfa()` not `updateMFA()`. Uppercase acronyms break SDK generation (`create_m_f_a` instead of `create_mfa`). In non-method identifiers (constants, config keys), fully capitalise: `cacheTTL`, `parseURL`.
- Don't double up namespace in file names. E.g. `Engine/Driver.php` not `Engine/EngineDriver.php` — namespace already provides context. Put implementations in nested subdirectories (e.g. `Engine/Driver/{Postgres,MySQL,Mongo}.php`).
- REST endpoints: plural nouns (`/collections` not `/collection`), kebab-case for multi-word paths (`/acme-challenge` not `/acmeChallenge`).

# Code style

- Never use "section header" style comments like `// ---` or `// ===` and if you see any, remove them.
- Prefer typed config objects over associative arrays. Use readonly classes with typed constructor properties where the language supports it.
- Use constants or enums instead of magic strings. PHP: backed enums (`enum Suit: string`). TypeScript: SCREAMING_SNAKE_CASE enum names with lowercase values.
- Don't impose arbitrary limits (max file sizes, max entries, etc.) unless there's a real technical constraint. Validate claimed sizes against actual file/container size instead.
- Full type hints on all parameters and return types. Catch errors at compile time, not runtime.
- One class/interface per file. Filename matches class name.
- Imports: alphabetical, one per statement, grouped by const/class/function.
- Single quotes for strings by default. Double quotes only when the string contains a single quote.
- Sparse updates — when updating a record, pass only changed attributes, not the full object.
- Domain-driven design — group business logic by domain. No helper files, no random global functions, no fat controllers.
- When working in a file, fix any nearby violations of the above rules in code closely scoped to your changes.

# PHP

- Singular nouns for namespaces: `Adapter` not `Adapters` — a namespace is a folder, plurality is implied.
- When extending a Utopia library in Appwrite or Cloud, use `src/Utopia` namespace: `Appwrite\Utopia\Database\Adapter\MySQL` not `Appwrite\Database\Adapter\MySQL`.
- Dependency versions: use `*` wildcard not `~`/`^` ranges. `"utopia-php/framework": "0.33.*"` not `"~0.33.0"`.
- First-class callable syntax: `$this->action(...)` not `[$this, 'action']`.
- Use `array_push($items, ...$new)` instead of `$items = array_merge($items, $new)` in loops — merge copies the entire array every iteration.
- Use `array_values()` after `unset()` or `array_unique()` to re-index and keep the array a list.
- `??` (null coalescing) for null/isset checks. `?:` (elvis) for falsy checks. `getenv()` never returns null, so use `?:` with it.
- Prefer `assertSame` over `assertEquals` in new PHPUnit tests — assertSame checks type and value.

# Testing

- There are no "pre-existing issues". If tests fail, fix them, regardless of when you think the issue was introduced.

# Workflow

- Don't stop mid-implementation to ask if I want to review. Keep going until done. Unnecessary pauses are disruptive.
- Never revert PR changes to work around missing dependencies. Add the dependency properly (e.g. as a VCS repository in composer.json).
- Never use shims or patch files for local dependencies. Edit source in the dependency repo, commit and push, then run the package manager update in the consuming repo.
- Format and lint before every commit. PHP: `composer lint` (Pint, PSR-12). Kotlin: ktlint. Rust: `cargo fmt` + `cargo clippy -D warnings`. JS/TS: Prettier.
- Conventional commits: `(type): subject` — types are `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`. Focus on "why" not "what".
- In Appwrite repos, PRs target the current version branch (e.g. `1.9.x`), not `main`. `main` is reserved for release management.

# Projects

All repos live in `~/Local/`. Primary ecosystem is Appwrite — backend platform, cloud hosting, edge, SDKs for 11+ languages, console, database/query libraries, and supporting infrastructure (proxy, websocket, audit, cache, framework). Most backend services are PHP 8.3+ on Swoole 6. Utopia PHP framework throughout — no Laravel/Symfony.

- **plotpals** — Kotlin Multiplatform + Compose Multiplatform. MVI architecture, offline-first with Store pattern, SQLDelight, Koin DI. Ktor 3 server with Exposed ORM.
- **claudear** — Rust. Automated issue triage/response with Discord, Slack, and Jira integrations. Docker + SQLite (named volumes for WAL compatibility).
- **infrastructure** — Terraform for DigitalOcean, Cloudflare, and cloud services.
