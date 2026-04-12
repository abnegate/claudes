---
name: kotlin-expert
description: House rules and load-bearing patterns for Kotlin 2.x / K2 / KMP. Covers K2 compiler migration (what breaks), Kotlin 2.x features (context parameters, explicit backing fields, multi-dollar interpolation, guard conditions, non-local break/continue, name-based destructuring), KMP (expect/actual, source sets, pitfalls), coroutines (structured concurrency, SupervisorJob, cancellation, StateFlow vs SharedFlow, Turbine testing), scope functions, delegation, inline/reified, sealed types, value classes, contracts, type system (Nothing/Unit/variance), null safety traps (platform types, Java interop), collections (sequence vs list, buildList/buildMap), operators, DSL building, testing (JUnit 5, coroutine tests), Gradle (version catalogs, convention plugins), and house naming. **Does not** re-teach basic syntax, basic null safety, basic collections, basic coroutines, or OOP. Android UI patterns live in android-expert. Use when writing or reviewing any Kotlin 2.x code.
---

# Kotlin Expert

Opinion and house-rule reference for **Kotlin 2.x / K2 / KMP**. **Assumes baseline Kotlin knowledge** (val/var, null safety basics, when, data classes, extensions, sealed classes, coroutine fundamentals) -- only what's house-specific, load-bearing, or shifts year-to-year.

Non-negotiable defaults:
- **Kotlin 2.1+ with K2 compiler.** All new projects use K2. Existing projects must migrate.
- Every class `internal` unless part of public API. Minimize visibility.
- Full type annotations on public API. Inferred types for locals and private members only.
- `data class` for value types, `data object` for singletons in sealed hierarchies, `object` for stateless utilities.
- `sealed interface` over `sealed class` unless you need shared state. Exhaustive `when` -- no `else` on sealed types.
- One class/interface per file. Filename matches top-level declaration.
- No abbreviations: `connection` not `conn`, `certificate` not `cert`. camelCase acronyms: `updateMfa()` not `updateMFA()`.
- Singular package nouns: `adapter` not `adapters`. No `Impl` suffix: `PostgresDriver` not `DriverImpl`.

---

## 1. K2 compiler -- what breaks

```kotlin
// K2 is default in Kotlin 2.0+ -- remove obsolete flags:
// languageVersion = "2.0"       // already default
// freeCompilerArgs += "-Xuse-k2" // removed
```

- **Smarter type inference** -- narrows types more aggressively. May resolve to a different overload. Audit overloaded functions.
- **Stricter synthetic property resolution** -- Java getter/setter ambiguity resolves differently. `getFoo()` vs `foo` may pick different overload.
- **Builder inference** -- `buildList { }` / `buildMap { }` infer from all usages, not just the first. May need explicit type params.
- **`@JvmStatic` visibility** -- `private` companion member via `@JvmStatic` is now a compile error.
- **Smart casts survive** through contracts, lambdas, and property access (K1 pessimistically widened). Adopt immediately.

---

## 2. Kotlin 2.x features

### 2.1 Context parameters (2.2+, replacing context receivers)

```kotlin
// Old (deprecated): context(Logger, Transaction)
context(logger: Logger, transaction: Transaction)
fun transferFunds(from: Account, to: Account, amount: Long) {
    logger.info("Transferring $amount")    // by parameter name, NOT `this`
    transaction.execute { from.debit(amount); to.credit(amount) }
}
```

- Access by name, not `this`. Cannot have two context params of the same type. Context params propagate to callees that require the same context.

### 2.2 Explicit backing fields (2.1+)

```kotlin
class Counter {
    val count: Int
        field = 0              // explicit backing field with initializer
        get() = field
    var name: String = ""
        set(value) { require(value.isNotBlank()); field = value.trim() }
}
```

Replaces the `_backing` + public getter pattern.

### 2.3 Multi-dollar string interpolation (2.1+)

```kotlin
val regex = $$"^\d+$$variable\d+$"   // $$ interpolates, bare $ is literal
val template = $$"""
    Dear $$name,
    Your balance is $100.00.         // no escaping needed
"""
```

### 2.4 Guard conditions in when (2.1+)

```kotlin
fun classify(response: Response) = when (response) {
    is Success if response.data.isEmpty() -> "empty"   // smart-cast in guard
    is Success                             -> "ok"
    is Error if response.code == 404       -> "not found"
    is Error if response.code in 500..599  -> "server error"
    is Error                               -> "client error"
}
```

### 2.5 Non-local break/continue in inline lambdas (2.1+)

```kotlin
for (file in files) {
    file.readLines().forEach { line ->
        if (line.startsWith("#")) continue    // outer for loop
        if (line == "END") break              // outer for loop
        process(line)
    }
}
// Only works with inline lambdas. Non-inline cannot use non-local break/continue.
```

### 2.6 Name-based destructuring (2.2+)

```kotlin
data class User(val name: String, val age: Int, val email: String)
val (email, name) = user   // matches by NAME, not position
// BREAKING CHANGE for existing positional destructuring. Audit all sites.
```

---

## 3. KMP patterns

### 3.1 Source set hierarchy

```
commonMain/           -- pure Kotlin, no platform APIs (default target)
androidMain/          -- Context, Lifecycle, etc.
iosMain/              -- UIKit, Foundation, Darwin
jvmMain/              -- JVM desktop
```

- Start in `commonMain`. Move to platform source set only when you must.
- No `expect` without a clear platform boundary. Intermediate source sets (`nativeMain`, `appleMain`) share cross-platform code.

### 3.2 Expect/actual

```kotlin
// commonMain
expect class PlatformFile(path: String) {
    fun readText(): String
    fun exists(): Boolean
}
// androidMain
actual class PlatformFile actual constructor(private val path: String) {
    actual fun readText(): String = java.io.File(path).readText()
    actual fun exists(): Boolean = java.io.File(path).exists()
}
```

Prefer `expect fun` for single functions. Consider `interface` + DI over expect/actual for complex implementations.

### 3.3 Common pitfalls

- `kotlinx.datetime` not `java.time` in common code. `kotlinx.io` not `java.io`.
- Ktor `HttpClient` needs per-platform engine. Declare engine in platform source sets, inject client.
- `Dispatchers.IO` is JVM/Android only. Use `Dispatchers.Default` or inject dispatcher in common code.
- `kotlinx.serialization` not Gson/Moshi (JVM-only).

---

## 4. Coroutines

### 4.1 Structured concurrency

```kotlin
coroutineScope {
    launch { task1() }   // if task1 fails, task2 is cancelled
    launch { task2() }
}
supervisorScope {
    launch { task1() }   // if task1 fails, task2 keeps running
    launch { task2() }
}
```

### 4.2 SupervisorJob gotchas

```kotlin
// WRONG -- SupervisorJob only supervises DIRECT children
val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
scope.launch {
    launch { failingTask() }  // failure cancels sibling -- inner scope is regular Job
    launch { otherTask() }
}
// RIGHT -- launch directly on the supervisor scope
scope.launch { failingTask() }   // independent
scope.launch { otherTask() }     // independent
```

### 4.3 Cancellation

```kotlin
// CancellationException is special -- NEVER swallow it
// WRONG:
try { suspendingWork() } catch (exception: Exception) { log(exception) }

// RIGHT:
try { suspendingWork() }
catch (exception: CancellationException) { throw exception }
catch (exception: Exception) { log(exception) }

// ensureActive() for cooperative cancellation in tight loops
suspend fun process(items: List<Item>) {
    for (item in items) { ensureActive(); handle(item) }
}
```

### 4.4 Scope lifecycle

- Scope MUST be tied to a lifecycle. `viewModelScope`, `lifecycleScope`, `runTest` TestScope.
- NEVER use `GlobalScope`. NEVER create `CoroutineScope()` without cancelling it.

### 4.5 Flow operators

```kotlin
searchQuery.flatMapLatest { repository.search(it) }   // cancels previous on new emission
ids.flatMapMerge(concurrency = 4) { flow { emit(fetch(it)) } }  // parallel
flow.distinctUntilChangedBy { it.id }                  // custom equality

// ALWAYS WhileSubscribed(5_000) unless truly app-scoped
val state = flow.stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)
```

### 4.6 StateFlow vs SharedFlow vs Channel

| Need | Use |
|---|---|
| Current value, UI state | `StateFlow` (conflates) |
| Event stream, no initial value | `SharedFlow(replay = 0)` |
| One-shot effects (nav, snackbar) | `Channel(BUFFERED).receiveAsFlow()` |

### 4.7 Testing with Turbine

```kotlin
@Test fun `emits items then completes`() = runTest {
    repository.observeItems().test {
        assertEquals(emptyList(), awaitItem())
        repository.insert(item)
        assertEquals(listOf(item), awaitItem())
        cancelAndIgnoreRemainingEvents()
    }
}
@Test fun `parallel flows`() = runTest {
    turbineScope {
        val a = flowA.testIn(this); val b = flowB.testIn(this)
        assertEquals(1, a.awaitItem()); assertEquals("x", b.awaitItem())
        a.cancel(); b.cancel()
    }
}
```

- `runTest` provides virtual time. `advanceUntilIdle()` / `advanceTimeBy()` for time control.
- `StandardTestDispatcher` for step-by-step, `UnconfinedTestDispatcher` for immediate.

---

## 5. Scope functions

```kotlin
val length = name?.let { it.trim().length }                // nullable transform
val result = connection.run { open(); query("SELECT 1") }  // receiver scope, return result
val csv = with(StringBuilder()) { appendLine("h"); toString() }  // non-extension run
val req = Request().apply { url = "..."; method = "POST" } // configure, return object
val user = createUser().also { analytics.track(it.id) }    // side effect, return object
```

| Return | Receiver (`this`) | Argument (`it`) |
|---|---|---|
| Lambda result | `run` / `with` | `let` |
| Object itself | `apply` | `also` |

---

## 6. Delegation

```kotlin
// by lazy -- SYNCHRONIZED (default), PUBLICATION (race-ok), NONE (single-thread only)
val heavy by lazy { ExpensiveObject() }
val cache by lazy(LazyThreadSafetyMode.NONE) { buildCache() }  // main-thread UI code

// by map
class Config(private val props: Map<String, Any?>) {
    val host: String by props   // delegates get() to map lookup
    val port: Int by props
}

// Observable / vetoable (stdlib)
var status: String by Delegates.observable("idle") { _, old, new -> log("$old -> $new") }
var age: Int by Delegates.vetoable(0) { _, _, new -> new >= 0 }

// Custom delegate
class Logged<T>(private var value: T) : ReadWriteProperty<Any?, T> {
    override fun getValue(thisRef: Any?, property: KProperty<*>): T = value
    override fun setValue(thisRef: Any?, property: KProperty<*>, value: T) {
        println("${property.name}: ${this.value} -> $value"); this.value = value
    }
}
```

---

## 7. Inline, reified, crossinline, noinline

```kotlin
// Reified -- runtime type access (requires inline)
inline fun <reified T> parseJson(json: String): T = Json.decodeFromString<T>(json)

// crossinline -- lambda cannot non-local return (needed in different execution context)
inline fun transaction(crossinline block: () -> Unit) {
    begin(); try { block(); commit() } catch (e: Exception) { rollback(); throw e }
}

// noinline -- opt lambda out of inlining (needed when storing the lambda)
inline fun execute(inlined: () -> Unit, noinline stored: () -> Unit) {
    inlined(); callbacks.add(stored)
}
```

- Don't inline large bodies -- code size bloats. Inline for small HOFs and reified generics only.
- Reified only works in `inline` functions. Without it, `T` is erased.

---

## 8. Sealed types

```kotlin
// PREFER sealed interface -- subtypes can implement multiple interfaces
sealed interface Result<out T> {
    data class Success<T>(val data: T) : Result<T>
    data class Failure(val error: Throwable) : Result<Nothing>
    data object Loading : Result<Nothing>
}

// sealed class only when subtypes need shared state
sealed class NetworkState(val timestamp: Long = System.currentTimeMillis()) {
    data class Connected(val speed: Int) : NetworkState()
    data object Disconnected : NetworkState()
}

// Exhaustive when -- NO else branch
fun handle(result: Result<User>) = when (result) {
    is Result.Success -> showUser(result.data)
    is Result.Failure -> showError(result.error)
    is Result.Loading -> showSpinner()
}
// Statement-position exhaustiveness trick:
when (intent) { is Intent.Load -> load(); is Intent.Refresh -> refresh() }.let {}
```

---

## 9. Value classes

```kotlin
@JvmInline value class UserId(val value: Long)
@JvmInline value class Email(val value: String) {
    init { require(value.contains('@')) { "Invalid email: $value" } }
}
```

- Single property only. Cannot extend classes (can implement interfaces).
- Boxing when: nullable, generic type parameter, assigned to interface type.
- Use for IDs, quantities, units, domain primitives needing type safety without allocation.

---

## 10. Contracts

```kotlin
@OptIn(ExperimentalContracts::class)
inline fun <T> measureTime(block: () -> T): Pair<T, Long> {
    contract { callsInPlace(block, InvocationKind.EXACTLY_ONCE) }
    val start = System.nanoTime(); val result = block()
    return result to (System.nanoTime() - start)
}

@OptIn(ExperimentalContracts::class)
fun requireNotBlank(value: String?): String {
    contract { returns() implies (value != null) }
    require(!value.isNullOrBlank()); return value  // smart cast, no !! needed
}
```

Still `@ExperimentalContracts` but widely used in stdlib. Use sparingly -- only when smart cast benefit is clear.

---

## 11. Type system

```kotlin
// Nothing -- never returns. Subtype of everything.
fun fail(message: String): Nothing = throw IllegalStateException(message)
val user: User = cache[id] ?: fail("Not found")  // compiles: Nothing <: User

// Variance: out = producer (covariant), in = consumer (contravariant)
interface Source<out T> { fun next(): T }
interface Sink<in T> { fun accept(item: T) }
fun copy(from: Array<out Number>, to: Array<in Number>) {
    for (i in from.indices) { to[i] = from[i] }
}
// Star projection: List<*> == List<out Any?>, safe read, unsafe write

// Reified type checks (inline only)
inline fun <reified T> filterByType(items: List<Any>): List<T> = items.filterIsInstance<T>()
```

---

## 12. Null safety traps

```kotlin
// Platform types from Java interop -- NEVER let them propagate
val name = javaObject.name           // String! -- no compiler check
val name: String = javaObject.name   // throws immediately if null (GOOD)
val name: String? = javaObject.name  // forces null check downstream (GOOD)

// !! chains are undebuggable
val city = user!!.address!!.city!!   // which was null?
val city = user?.address?.city ?: throw DomainException("Missing city for ${user?.id}")

// Safe cast
val number: Int? = value as? Int     // null instead of ClassCastException

// ?.let vs if-null-check
if (user != null) { println(user.name); println(user.email) }   // smart cast in scope
user?.let { repository.save(it) }                                 // single transform
// NEVER: name?.let { println(it) }  -- use if (name != null)
```

---

## 13. Collections

```kotlin
// Sequence vs List: use Sequence when 3+ ops AND 1000+ items AND early termination
items.asSequence().filter { it.isActive }.map { it.name }.take(10).toList()

// buildList/buildMap/buildSet -- prefer over mutable + toList()
val items = buildList { add(header); addAll(fetchItems()); if (show) add(footer) }
val lookup = buildMap<String, User> { users.forEach { put(it.id, it) } }

// groupBy (1:N), associateBy (1:1, last wins), partition (split by predicate)
val byDept = employees.groupBy { it.department }
val byId = employees.associateBy { it.id }
val (active, inactive) = employees.partition { it.isActive }
```

---

## 14. Operators and DSL building

```kotlin
// Operator overloading
data class Vector(val x: Double, val y: Double) {
    operator fun plus(other: Vector) = Vector(x + other.x, y + other.y)
    operator fun times(scalar: Double) = Vector(x * scalar, y * scalar)
}
class Matrix(private val data: Array<DoubleArray>) {
    operator fun get(row: Int, col: Int) = data[row][col]
    operator fun set(row: Int, col: Int, v: Double) { data[row][col] = v }
}
class Validator(private val rules: List<Rule>) {
    operator fun invoke(input: String): Boolean = rules.all { it.check(input) }
}

// DSL building -- lambda with receiver + @DslMarker
@DslMarker annotation class RoutingDsl

@RoutingDsl class RouteBuilder {
    private val routes = mutableListOf<Route>()
    fun get(path: String, handler: suspend (Request) -> Response) { routes.add(Route("GET", path, handler)) }
    fun post(path: String, handler: suspend (Request) -> Response) { routes.add(Route("POST", path, handler)) }
    fun build(): List<Route> = routes.toList()
}
fun routing(init: RouteBuilder.() -> Unit): List<Route> = RouteBuilder().apply(init).build()
// @DslMarker prevents accidental access to outer receivers in nested lambdas
```

---

## 15. Testing

```kotlin
// JUnit 5 + kotlin.test for cross-platform assertions
class ParserTest {
    @Test fun `parses valid input`() {
        assertEquals("value", Parser.parse("key=value")["key"])
    }
    @Test fun `throws on malformed input`() {
        assertFailsWith<ParseException> { Parser.parse("invalid") }
    }
}

// Parameterized tests
@ParameterizedTest
@CsvSource("user@example.com, true", "invalid, false", "'', false")
fun `validates emails`(input: String, expected: Boolean) {
    assertEquals(expected, EmailValidator.isValid(input))
}

// assertSoftly -- reports ALL failures, not just first
assertSoftly(user) { name shouldBe "Alice"; age shouldBe 30; email shouldBe "alice@example.com" }

// Coroutine tests
@Test fun `cancellation cleans up`() = runTest {
    val resource = TestResource()
    val job = launch { resource.longRunning() }
    advanceTimeBy(1_000); job.cancelAndJoin()
    assertTrue(resource.isClosed)
}
```

---

## 16. Build -- Gradle Kotlin DSL

### 16.1 Version catalogs

```toml
# gradle/libs.versions.toml
[versions]
kotlin = "2.1.20"
coroutines = "1.10.1"
ktor = "3.1.2"
[libraries]
coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "coroutines" }
coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "coroutines" }
[plugins]
kotlin-multiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
```

### 16.2 Convention plugins

```kotlin
// build-logic/convention/src/main/kotlin/kotlin-library.gradle.kts
plugins { kotlin("jvm"); kotlin("plugin.serialization") }
kotlin {
    jvmToolchain(21)
    compilerOptions { allWarningsAsErrors.set(true); freeCompilerArgs.addAll("-Xjsr305=strict") }
}
dependencies { testImplementation(kotlin("test")) }
```

- **`build-logic/` included build, not `buildSrc`** -- buildSrc invalidates entire build cache on change.
- Version catalogs for versions. Convention plugins for shared config. No copy-pasting.
- `jvmToolchain(21)` pins JDK. `allWarningsAsErrors = true` for all modules.
- `./gradlew spotlessApply` before every commit. CI runs `spotlessCheck`.

---

## 17. Anti-pattern catalog

| # | Anti-pattern | Correct approach |
|---|---|---|
| 1 | `catch (e: Exception)` in coroutine code | Catch specific types; always rethrow `CancellationException` |
| 2 | `GlobalScope.launch { }` | Inject `CoroutineScope` tied to a lifecycle |
| 3 | Platform type propagation from Java | Assign to explicitly typed `val` at the boundary |
| 4 | `object Foo : SealedType` | `data object Foo : SealedType` |
| 5 | `sealed class` when no shared state | `sealed interface` |
| 6 | `else` on sealed type `when` | Omit -- let compiler enforce exhaustiveness |
| 7 | `SharingStarted.Eagerly` | `WhileSubscribed(5_000)` unless truly app-scoped |
| 8 | `runBlocking` in production | `suspend fun` or `coroutineScope { }` |
| 9 | Mutable collection in public API | `List<T>`, `Map<K,V>`, `Set<T>` |
| 10 | `updateMFA()` / `toJSON()` | `updateMfa()` / `toJson()` -- camelCase acronyms |
| 11 | `package com.example.validators` | `validator` -- singular nouns |
| 12 | `DriverImpl` / `ServiceImpl` | `PostgresDriver` / `HttpService` |
| 13 | `delay()` in tests | `advanceTimeBy()` / `advanceUntilIdle()` |
| 14 | `var` accumulation in functional chains | `fold` / `buildList` / `buildMap` |
| 15 | Raw strings for closed sets | Enum or sealed interface |
| 16 | `data class` for entities with identity | Regular class with `equals`/`hashCode` on ID |
| 17 | Version strings in `build.gradle.kts` | Version catalogs |
| 18 | `buildSrc` for convention plugins | `build-logic/` included build |
| 19 | `Dispatchers.IO` in common KMP code | Inject dispatcher or use `Dispatchers.Default` |
| 20 | `!!` chains (`a!!.b!!.c!!`) | Safe calls + meaningful error |
| 21 | `?.let { }` for simple null checks | `if (x != null)` -- smart cast in scope |
| 22 | `java.time` / Gson / Moshi in KMP | `kotlinx.datetime` / `kotlinx.serialization` |
| 23 | Inline function with large body | Only inline small HOFs and reified generics |
| 24 | `stateIn` without subscribers keeps hot | `WhileSubscribed(5_000)` |
| 25 | `companion object { const val }` for config | Top-level `const val` or typed config object |
