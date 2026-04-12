# kotlin-expert

House rules and load-bearing patterns for Kotlin 2.x / K2 / KMP. **Assumes baseline Kotlin knowledge** -- this skill only covers what's house-specific, what's load-bearing, or what's new enough that training data is unreliable.

## What it covers

- **K2 compiler migration** -- what changed, what breaks, stricter type inference and resolution, builder inference changes
- **Kotlin 2.x features** -- context parameters (replacing context receivers), explicit backing fields, multi-dollar string interpolation, guard conditions in when, non-local break/continue, name-based destructuring, with gotchas for each
- **KMP patterns** -- expect/actual, source set hierarchy, platform-specific code organization, common pitfalls (kotlinx.datetime, kotlinx.io, Dispatchers.IO)
- **House naming rules** -- full words, camelCase acronyms, singular packages, no Impl suffix
- **Anti-pattern catalog** -- house-specific and 2.x-related patterns to refuse on sight

## What it does NOT cover

Deliberately omitted because it's well-documented in training data or covered by other skills:

- Coroutines (structured concurrency, SupervisorJob, cancellation, StateFlow/SharedFlow, Turbine) -- also in android-expert
- Scope functions, delegation, inline/reified, sealed types, value classes, contracts
- Type system (Nothing, variance, star projection), null safety traps, collections
- Operators, DSL building, testing (JUnit 5, coroutine tests)
- Build (version catalogs, convention plugins) -- also in android-expert
- Basic Kotlin syntax, OOP, standard Gradle usage

Android-specific patterns (Compose, MVI, Navigation, Room, Material 3, edge-to-edge, DI with Koin) live in `android-expert`. Runtime-specific patterns (Swoole, PHP servers) live in their respective skills.

## Target

- **Kotlin 2.1+ with K2 compiler.**
- Standard toolchain: Gradle with Kotlin DSL, version catalogs, ktlint via spotless.
- Any Kotlin project: Android, KMP, backend (Ktor), libraries.
