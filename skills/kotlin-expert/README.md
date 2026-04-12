# kotlin-expert

House rules and load-bearing patterns for Kotlin 2.x / K2 / KMP. **Assumes baseline Kotlin knowledge** -- this skill only covers what's house-specific, what's load-bearing, or what shifts year-to-year.

## What it covers

- **K2 compiler migration** -- what changed, what breaks, stricter type inference and resolution, builder inference changes
- **Kotlin 2.x features** -- context parameters (replacing context receivers), explicit backing fields, multi-dollar string interpolation, guard conditions in when, non-local break/continue, name-based destructuring, with gotchas for each
- **KMP patterns** -- expect/actual, source set hierarchy, platform-specific code organization, common pitfalls (kotlinx.datetime, kotlinx.io, Dispatchers.IO)
- **Coroutines** -- structured concurrency rules, SupervisorJob gotchas, cancellation behavior (CancellationException traps), CoroutineScope lifecycle, flow operators (flatMapLatest, stateIn, debounce), StateFlow vs SharedFlow vs Channel decision rules, testing with Turbine + kotlinx-coroutines-test
- **Scope functions** -- let/run/with/apply/also decision tree with return-type and receiver/argument axes
- **Delegation** -- by lazy (thread safety modes), by map, custom delegates, observable/vetoable
- **Inline/reified** -- when to use, limitations, crossinline/noinline
- **Sealed types** -- sealed interface vs sealed class decision, exhaustive when without else
- **Value classes** -- when to use, boxing gotchas, limitations
- **Contracts** -- callsInPlace, returns, returnsNotNull for smart casts
- **Type system** -- Nothing/Unit, variance (in/out/star), reified type checks
- **Null safety traps** -- platform types from Java interop, !! chains, safe cast as?, ?.let vs if-null-check
- **Collections** -- sequence vs list decision rule, buildList/buildMap/buildSet, groupBy/associateBy/partition
- **Operator overloading** -- get/set/invoke/compareTo/contains/iterator conventions
- **DSL building** -- lambda with receiver, @DslMarker, type-safe builders
- **Testing** -- JUnit 5 + kotlin.test, data-driven tests, assertSoftly, coroutine test patterns
- **Build** -- Gradle Kotlin DSL with version catalogs, convention plugins in build-logic/, ktlint via spotless
- **House naming rules** -- full words, camelCase acronyms, singular packages, no Impl suffix
- **Anti-pattern catalog** -- 25 patterns to refuse on sight

## What it does NOT cover

Deliberately omitted because it's already in the training data:

- Basic Kotlin syntax (val/var, fun, class, when, if/else, for loops)
- Basic null safety (?, ?., ?:, !!)
- Basic collections (map, filter, reduce, forEach)
- Basic coroutine concepts (what suspend means, what launch/async do)
- Standard OOP (classes, interfaces, inheritance, data classes, enums)
- Basic Gradle usage

Android-specific patterns (Compose, MVI, Navigation, Room, Material 3, edge-to-edge, DI with Koin) live in `android-expert`. Runtime-specific patterns (Swoole, PHP servers) live in their respective skills.

## Target

- **Kotlin 2.1+ with K2 compiler.**
- Standard toolchain: Gradle with Kotlin DSL, version catalogs, ktlint via spotless.
- Any Kotlin project: Android, KMP, backend (Ktor), libraries.
