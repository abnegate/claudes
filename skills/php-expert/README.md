# php-expert

House rules and load-bearing patterns for writing production PHP 8.3+ code. **Assumes baseline PHP 8.0–8.2 knowledge** — this skill only covers what's house-specific, what's load-bearing, or what shifts year-to-year.

## What it covers

- **Version landscape** — what's EOL / security / active as of April 2026
- **Typed class constants** — the `public const string FOO = '...';` form (easy to forget the type keyword)
- **`#[\Override]` discipline** — on every override, always
- **Class defaults** — `final` + `private readonly` promoted, `readonly class` for DTOs
- **Enum house idiom** — `values()`, `is<State>()`, `match`-based description methods with no `default:`
- **PHP 8.4 gotchas** — property hook limitations, asymmetric visibility, `new Foo()->bar()`, `array_find`/`array_any`/`array_all`, implicit nullable deprecation
- **`declare(strict_types=1)`** — match-the-repo rule
- **Naming rules** — singular namespaces, no abbreviations, camelCase acronyms in method names (SDK generation reason), no doubled-up filenames
- **Imports** — alphabetical, one per statement, grouped `const` / `class` / `function`
- **Domain grouping** — no `helpers/`, no `utils/`, no `common.php`
- **Sparse updates + fix-nearby-violations discipline**
- **Project structure** — `src/` vs `app/` vs `bin/` vs `tests/`, `autoload-dev` for test code
- **Composer** — constraint style discipline (pick one per project), VCS repos for forks, standard script names, deploy flags, platform pinning
- **Pint config** — exact `pint.json` rules
- **PHPStan** — target `level: max` in greenfield, baseline discipline
- **Rector** — typical `rector.php` for 8.4 + PHPUnit 12 migration
- **Typed exceptions** — `public const string` error codes, `ENTITY_ERRORTYPE` naming, custom exceptions with public readonly context fields, exception hierarchy, `finally` vs log-and-rethrow
- **Array idioms worth the rule** — `array_push($a, ...$new)` vs `array_merge` in loops, PHPStan shape annotations
- **PHPUnit 12** — attribute migration reminder, `assertSame` always, unit vs e2e hard line, never mocking the database, mandatory regression tests
- **House anti-patterns** — the specific things to refuse on sight

## What it does NOT cover

Deliberately omitted because it's already in the training data:

- Basic language syntax — constructor promotion, readonly, enums (intro), `match`, nullsafe, named args, first-class callables, arrow functions, null coalescing
- Elementary PHP 8.0–8.2 features
- PSR-4 / PSR-12 basics
- Trivial composer usage
- Basic PHPUnit structure

Framework-specific patterns (HTTP kernels, route builders, DI containers, ORMs, queue adapters, event buses) belong in per-framework skills. Runtime-specific patterns (Swoole coroutines, servers, channels, pools) live in `swoole-expert`.

## Target

- **PHP 8.3 minimum, PHP 8.4 preferred.**
- Standard toolchain: Composer 2, PHPUnit 12, PHPStan 2, Laravel Pint, Rector.
- Any modern PHP project that isn't tied to a specific framework.
